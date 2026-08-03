import uuid

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from empresas.models import Empresa


class Familia(models.Model):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name="familias",
    )
    nombre = models.CharField(max_length=120)
    descripcion = models.TextField(blank=True)
    imagen = models.ImageField(
        upload_to="catalogo/familias/",
        blank=True,
        null=True,
    )
    imagen_url = models.URLField(
        blank=True,
        help_text="URL externa futura para almacenamiento en linea.",
    )
    activa = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name = "familia"
        verbose_name_plural = "familias"
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "nombre"],
                name="familia_nombre_unico_por_empresa",
            )
        ]

    def __str__(self):
        return f"{self.nombre} ({self.empresa})"

    @property
    def imagen_final(self):
        if self.imagen_url:
            return self.imagen_url

        if self.imagen:
            return self.imagen.url

        return None

    def save(self, *args, **kwargs):
        if not self.pk and self.orden == 0:
            ultimo_orden = (
                Familia.objects.filter(empresa=self.empresa)
                .aggregate(max_orden=models.Max("orden"))
                .get("max_orden")
                or 0
            )
            self.orden = ultimo_orden + 1

        super().save(*args, **kwargs)


class Categoria(models.Model):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name="categorias",
    )
    familia = models.ForeignKey(
        Familia,
        on_delete=models.PROTECT,
        related_name="categorias",
    )
    nombre = models.CharField(max_length=120)
    descripcion = models.TextField(blank=True)
    imagen = models.ImageField(
        upload_to="catalogo/categorias/",
        blank=True,
        null=True,
    )
    imagen_url = models.URLField(
        blank=True,
        help_text="URL externa futura para almacenamiento en linea.",
    )
    activa = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["familia__orden", "orden", "nombre"]
        verbose_name = "categoria"
        verbose_name_plural = "categorias"
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "nombre"],
                name="categoria_nombre_unico_por_empresa",
            )
        ]

    def __str__(self):
        return f"{self.nombre} - {self.familia.nombre}"

    @property
    def imagen_final(self):
        if self.imagen_url:
            return self.imagen_url

        if self.imagen:
            return self.imagen.url

        return None

    def clean(self):
        super().clean()
        if self.familia_id and self.empresa_id != self.familia.empresa_id:
            raise ValidationError(
                {"familia": "La categoria debe pertenecer a una familia de la misma empresa."}
            )

    def save(self, *args, **kwargs):
        if not self.pk and self.orden == 0:
            ultimo_orden = (
                Categoria.objects.filter(familia=self.familia)
                .aggregate(max_orden=models.Max("orden"))
                .get("max_orden")
                or 0
            )
            self.orden = ultimo_orden + 1

        super().save(*args, **kwargs)


class Producto(models.Model):
    class TipoItem(models.TextChoices):
        PRODUCTO_FISICO = "producto_fisico", "Producto fisico"
        SERVICIO = "servicio", "Servicio"

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name="productos",
    )
    familia = models.ForeignKey(
        Familia,
        on_delete=models.PROTECT,
        related_name="productos",
    )
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name="productos",
    )
    tipo_item = models.CharField(
        max_length=20,
        choices=TipoItem.choices,
        default=TipoItem.PRODUCTO_FISICO,
        help_text=(
            "En empresas mixtas indica si se controla existencia o si es un servicio."
        ),
    )
    codigo_interno = models.CharField(max_length=80, editable=False)
    codigo_barra = models.CharField(max_length=80, null=True, blank=True)
    nombre = models.CharField(max_length=180)
    descripcion = models.TextField(blank=True)
    imagen_principal = models.ImageField(
        upload_to="catalogo/productos/",
        blank=True,
        null=True,
    )
    imagen_url = models.URLField(
        blank=True,
        help_text="URL externa futura para almacenamiento en linea.",
    )
    precio = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    existencia = models.PositiveIntegerField(default=0)
    existencia_minima = models.PositiveIntegerField(
        default=0,
        help_text="Cantidad minima para alertas internas de inventario bajo.",
    )
    orden_destacado = models.PositiveIntegerField(
        default=0,
        help_text="Prioridad manual para productos mas vendidos o destacados.",
    )
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "producto"
        verbose_name_plural = "productos"
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "codigo_barra"],
                name="producto_codigo_barra_unico_por_empresa",
            ),
            models.UniqueConstraint(
                fields=["empresa", "codigo_interno"],
                name="producto_codigo_interno_unico_por_empresa",
            ),
        ]

    def __str__(self):
        return f"{self.nombre} - {self.codigo_venta}"

    def save(self, *args, **kwargs):
        es_nuevo = self.pk is None
        self._aplicar_tipo_segun_empresa()
        self.codigo_barra = (self.codigo_barra or "").strip() or None

        if not self.codigo_interno:
            self.codigo_interno = self._generar_codigo_interno()

        if es_nuevo and self.controla_inventario:
            self.existencia = 0

        self.clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        self._aplicar_tipo_segun_empresa()

        if self.controla_inventario and not self.codigo_barra:
            raise ValidationError(
                {"codigo_barra": "Los productos fisicos requieren codigo de barras."}
            )

        if self.familia_id and self.empresa_id != self.familia.empresa_id:
            raise ValidationError(
                {"familia": "El producto debe pertenecer a una familia de la misma empresa."}
            )

        if self.categoria_id and self.empresa_id != self.categoria.empresa_id:
            raise ValidationError(
                {"categoria": "El producto debe pertenecer a una categoria de la misma empresa."}
            )

        if (
            self.categoria_id
            and self.familia_id
            and self.categoria.familia_id != self.familia_id
        ):
            raise ValidationError(
                {"categoria": "La categoria debe pertenecer a la familia seleccionada."}
            )

        self._validar_imagen_segun_empresa()
        self._validar_cambio_tipo_item()

    def _validar_imagen_segun_empresa(self):
        if (
            not self.empresa_id
            or self.empresa.productos_con_imagen
            or (not self.imagen_principal and not self.imagen_url)
        ):
            return

        imagen_modificada = self._state.adding
        if not imagen_modificada:
            original = (
                type(self)
                .objects.filter(pk=self.pk)
                .values("imagen_principal", "imagen_url")
                .first()
            )
            imagen_modificada = original is None or (
                (original["imagen_principal"] or "")
                != (self.imagen_principal.name if self.imagen_principal else "")
                or (original["imagen_url"] or "") != (self.imagen_url or "")
            )

        if imagen_modificada:
            raise ValidationError(
                {
                    "imagen_principal": (
                        "Esta empresa desactivo las imagenes individuales "
                        "de productos."
                    )
                }
            )

    @property
    def codigo_venta(self):
        return self.codigo_barra or self.codigo_interno

    @property
    def controla_inventario(self):
        if not self.empresa_id:
            return self.tipo_item == self.TipoItem.PRODUCTO_FISICO

        if self.empresa.modo_inventario == Empresa.ModoInventario.INVENTARIADO:
            return True

        if self.empresa.modo_inventario == Empresa.ModoInventario.SIN_INVENTARIO:
            return False

        return self.tipo_item == self.TipoItem.PRODUCTO_FISICO

    @property
    def imagen_final(self):
        if self.empresa_id and not self.empresa.productos_con_imagen:
            return None

        if self.imagen_url:
            return self.imagen_url

        if self.imagen_principal:
            return self.imagen_principal.url

        return None

    @property
    def agotado(self):
        if not self.controla_inventario:
            return False

        return self.existencia == 0

    @property
    def inventario_bajo(self):
        if not self.controla_inventario:
            return False

        return self.existencia > 0 and self.existencia <= self.existencia_minima

    @property
    def estado_inventario(self):
        if not self.controla_inventario:
            return "no_aplica"

        if self.agotado:
            return "agotado"

        if self.inventario_bajo:
            return "bajo"

        return "ok"

    def _aplicar_tipo_segun_empresa(self):
        if not self.empresa_id:
            return

        if self.empresa.modo_inventario == Empresa.ModoInventario.INVENTARIADO:
            self.tipo_item = self.TipoItem.PRODUCTO_FISICO
        elif self.empresa.modo_inventario == Empresa.ModoInventario.SIN_INVENTARIO:
            self.tipo_item = self.TipoItem.SERVICIO

    def _validar_cambio_tipo_item(self):
        if not self.pk:
            return

        tipo_anterior = (
            Producto.objects.filter(pk=self.pk)
            .values_list("tipo_item", flat=True)
            .first()
        )
        if not tipo_anterior or tipo_anterior == self.tipo_item:
            return

        if self.existencia > 0 or self.movimientos_inventario.exists():
            raise ValidationError(
                {
                    "tipo_item": (
                        "No se puede cambiar el tipo porque el producto tiene "
                        "existencia o movimientos de inventario."
                    )
                }
            )

    def _generar_codigo_interno(self):
        prefijo = (
            "SRV"
            if self.tipo_item == self.TipoItem.SERVICIO
            else "PRD"
        )

        while True:
            codigo = f"{prefijo}-{uuid.uuid4().hex[:12].upper()}"
            if not Producto.objects.filter(
                empresa_id=self.empresa_id,
                codigo_interno=codigo,
            ).exists():
                return codigo


class PaqueteCatalogo(models.Model):
    class Tipo(models.TextChoices):
        COMBO = "combo", "Combo"
        PERFIL = "perfil", "Perfil"

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name="paquetes_catalogo",
    )
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    codigo = models.CharField(max_length=80)
    nombre = models.CharField(max_length=180)
    descripcion = models.TextField(blank=True)
    precio_normal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    precio_paquete = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    porcentaje_descuento = models.PositiveSmallIntegerField(
        default=0,
        validators=[MaxValueValidator(100)],
    )
    imagen = models.ImageField(
        upload_to="catalogo/paquetes/",
        blank=True,
        null=True,
    )
    imagen_url = models.URLField(
        blank=True,
        help_text="URL externa futura para almacenamiento en linea.",
    )
    destacado = models.BooleanField(
        default=False,
        help_text="Usado para mostrar combos destacados en inicio.",
    )
    activo = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0)
    productos = models.ManyToManyField(
        Producto,
        through="PaqueteProducto",
        related_name="paquetes_catalogo",
        blank=True,
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name = "paquete de catalogo"
        verbose_name_plural = "paquetes de catalogo"
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "codigo"],
                name="paquete_catalogo_codigo_unico_por_empresa",
            )
        ]
        indexes = [
            models.Index(fields=["empresa", "tipo", "activo", "orden"]),
            models.Index(fields=["empresa", "tipo", "destacado", "activo", "orden"]),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.nombre}"

    @property
    def imagen_final(self):
        if self.imagen_url:
            return self.imagen_url

        if self.imagen:
            return self.imagen.url

        return None

    @property
    def agotado(self):
        items = self.items_productos.select_related("producto").all()
        return items.exists() and any(
            item.producto.controla_inventario
            and item.producto.existencia < item.cantidad
            for item in items
        )

    def clean(self):
        super().clean()

        if self.precio_paquete > self.precio_normal:
            raise ValidationError(
                {"precio_paquete": "El precio del paquete no puede superar el precio normal."}
            )

    def save(self, *args, **kwargs):
        if not self.pk and self.orden == 0:
            ultimo_orden = (
                PaqueteCatalogo.objects.filter(empresa=self.empresa, tipo=self.tipo)
                .aggregate(max_orden=models.Max("orden"))
                .get("max_orden")
                or 0
            )
            self.orden = ultimo_orden + 1

        super().save(*args, **kwargs)


class PaqueteProducto(models.Model):
    paquete = models.ForeignKey(
        PaqueteCatalogo,
        on_delete=models.CASCADE,
        related_name="items_productos",
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name="items_paquetes",
    )
    cantidad = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["orden", "producto__nombre"]
        verbose_name = "producto de paquete"
        verbose_name_plural = "productos de paquete"
        constraints = [
            models.UniqueConstraint(
                fields=["paquete", "producto"],
                name="paquete_producto_unico",
            )
        ]

    def __str__(self):
        return f"{self.paquete} - {self.producto}"

    def clean(self):
        super().clean()

        if self.paquete_id and self.producto_id:
            if self.paquete.empresa_id != self.producto.empresa_id:
                raise ValidationError(
                    {"producto": "El producto debe pertenecer a la misma empresa del paquete."}
                )

    def save(self, *args, **kwargs):
        if not self.pk and self.orden == 0:
            ultimo_orden = (
                PaqueteProducto.objects.filter(paquete=self.paquete)
                .aggregate(max_orden=models.Max("orden"))
                .get("max_orden")
                or 0
            )
            self.orden = ultimo_orden + 1

        super().save(*args, **kwargs)
