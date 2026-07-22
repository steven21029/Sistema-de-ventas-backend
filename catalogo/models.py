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
    codigo_barra = models.CharField(max_length=80)
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
            )
        ]

    def __str__(self):
        return f"{self.nombre} - {self.codigo_barra}"

    def save(self, *args, **kwargs):
        if not self.pk:
            self.existencia = 0

        super().save(*args, **kwargs)

    def clean(self):
        super().clean()

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

    @property
    def imagen_final(self):
        if self.imagen_url:
            return self.imagen_url

        if self.imagen_principal:
            return self.imagen_principal.url

        return None

    @property
    def agotado(self):
        return self.existencia == 0

    @property
    def inventario_bajo(self):
        return self.existencia > 0 and self.existencia <= self.existencia_minima

    @property
    def estado_inventario(self):
        if self.agotado:
            return "agotado"

        if self.inventario_bajo:
            return "bajo"

        return "ok"


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
        productos = self.productos.all()
        return productos.exists() and any(producto.agotado for producto in productos)

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
