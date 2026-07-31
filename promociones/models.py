from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from catalogo.models import PaqueteCatalogo, Producto
from empresas.models import Empresa


class BannerPromocional(models.Model):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name="banners_promocionales",
    )
    titulo = models.CharField(max_length=160)
    subtitulo = models.TextField(blank=True)
    texto_boton = models.CharField(max_length=60, blank=True)
    url_boton = models.CharField(
        max_length=240,
        blank=True,
        help_text="Ruta interna como /promociones/oferta-1 o URL externa.",
    )
    imagen = models.ImageField(
        upload_to="promociones/banners/",
        blank=True,
        null=True,
    )
    imagen_url = models.URLField(
        blank=True,
        help_text="URL externa futura para almacenamiento en linea.",
    )
    texto_alternativo = models.CharField(max_length=180, blank=True)
    orden = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)
    fecha_inicio = models.DateTimeField(null=True, blank=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["orden", "-fecha_creacion", "-id"]
        verbose_name = "banner promocional"
        verbose_name_plural = "banners promocionales"
        indexes = [
            models.Index(fields=["empresa", "activo", "orden"]),
            models.Index(fields=["empresa", "fecha_inicio", "fecha_fin"]),
        ]

    def __str__(self):
        return f"{self.empresa} - {self.titulo}"

    @property
    def esta_vigente(self):
        ahora = timezone.now()
        if not self.activo:
            return False

        if self.fecha_inicio and self.fecha_inicio > ahora:
            return False

        if self.fecha_fin and self.fecha_fin < ahora:
            return False

        return True

    def clean(self):
        super().clean()
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            raise ValidationError(
                {"fecha_fin": "La fecha final no puede ser menor que la fecha inicial."}
            )

        if not self.imagen and not self.imagen_url:
            raise ValidationError(
                {"imagen": "Debes agregar una imagen local o una URL externa."}
            )

    def save(self, *args, **kwargs):
        if not self.pk and self.orden == 0:
            ultimo_orden = (
                BannerPromocional.objects.filter(empresa=self.empresa)
                .aggregate(max_orden=models.Max("orden"))
                .get("max_orden")
                or 0
            )
            self.orden = ultimo_orden + 1

        self.full_clean()
        super().save(*args, **kwargs)


class OfertaPromocional(models.Model):
    class Tipo(models.TextChoices):
        PRODUCTO = "producto", "Producto"
        PRODUCTOS = "productos", "Varios productos"
        PAQUETE = "paquete", "Combo o perfil"

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name="ofertas_promocionales",
    )
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    codigo = models.CharField(max_length=80)
    titulo = models.CharField(max_length=160)
    descripcion = models.TextField(blank=True)
    precio_normal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    precio_oferta = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    porcentaje_descuento = models.PositiveSmallIntegerField(
        default=0,
        validators=[MaxValueValidator(100)],
    )
    imagen = models.ImageField(
        upload_to="promociones/ofertas/",
        blank=True,
        null=True,
    )
    imagen_url = models.URLField(
        blank=True,
        help_text="URL externa futura para almacenamiento en linea.",
    )
    url_destino = models.CharField(
        max_length=240,
        blank=True,
        help_text="Ruta interna o URL externa para abrir el detalle de la oferta.",
    )
    paquete = models.ForeignKey(
        PaqueteCatalogo,
        on_delete=models.PROTECT,
        related_name="ofertas_promocionales",
        null=True,
        blank=True,
    )
    productos = models.ManyToManyField(
        Producto,
        through="OfertaProducto",
        related_name="ofertas_promocionales",
        blank=True,
    )
    orden = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)
    fecha_inicio = models.DateTimeField(null=True, blank=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["orden", "-fecha_creacion", "-id"]
        verbose_name = "oferta promocional"
        verbose_name_plural = "ofertas promocionales"
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "codigo"],
                name="oferta_promocional_codigo_unico_por_empresa",
            )
        ]
        indexes = [
            models.Index(fields=["empresa", "tipo", "activo", "orden"]),
            models.Index(fields=["empresa", "fecha_inicio", "fecha_fin"]),
        ]

    def __str__(self):
        return f"{self.empresa} - {self.titulo}"

    @property
    def esta_vigente(self):
        ahora = timezone.now()
        if not self.activo:
            return False

        if self.fecha_inicio and self.fecha_inicio > ahora:
            return False

        if self.fecha_fin and self.fecha_fin < ahora:
            return False

        return True

    @property
    def imagen_final(self):
        if self.imagen_url:
            return self.imagen_url

        if self.imagen:
            return self.imagen.url

        return None

    def clean(self):
        super().clean()

        if self.fecha_inicio and self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            raise ValidationError(
                {"fecha_fin": "La fecha final no puede ser menor que la fecha inicial."}
            )

        if self.precio_oferta > self.precio_normal:
            raise ValidationError(
                {"precio_oferta": "El precio de oferta no puede superar el precio normal."}
            )

        if self.paquete_id and self.paquete.empresa_id != self.empresa_id:
            raise ValidationError(
                {"paquete": "El paquete debe pertenecer a la misma empresa de la oferta."}
            )

        if self.tipo == self.Tipo.PAQUETE and not self.paquete_id:
            raise ValidationError(
                {"paquete": "Las ofertas de combo o perfil deben seleccionar un paquete."}
            )

    def save(self, *args, **kwargs):
        if not self.pk and self.orden == 0:
            ultimo_orden = (
                OfertaPromocional.objects.filter(empresa=self.empresa)
                .aggregate(max_orden=models.Max("orden"))
                .get("max_orden")
                or 0
            )
            self.orden = ultimo_orden + 1

        self.full_clean()
        super().save(*args, **kwargs)


class OfertaProducto(models.Model):
    oferta = models.ForeignKey(
        OfertaPromocional,
        on_delete=models.CASCADE,
        related_name="items_productos",
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name="items_ofertas",
    )
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["orden", "producto__nombre"]
        verbose_name = "producto de oferta"
        verbose_name_plural = "productos de oferta"
        constraints = [
            models.UniqueConstraint(
                fields=["oferta", "producto"],
                name="oferta_producto_unico",
            )
        ]

    def __str__(self):
        return f"{self.oferta} - {self.producto}"

    def clean(self):
        super().clean()

        if self.oferta_id and self.producto_id:
            if self.oferta.empresa_id != self.producto.empresa_id:
                raise ValidationError(
                    {"producto": "El producto debe pertenecer a la misma empresa de la oferta."}
                )

    def save(self, *args, **kwargs):
        if not self.pk and self.orden == 0:
            ultimo_orden = (
                OfertaProducto.objects.filter(oferta=self.oferta)
                .aggregate(max_orden=models.Max("orden"))
                .get("max_orden")
                or 0
            )
            self.orden = ultimo_orden + 1

        super().save(*args, **kwargs)


class DescuentoPromocional(models.Model):
    class Alcance(models.TextChoices):
        TODOS = "todos", "Todos los articulos"
        SELECCIONADOS = "seleccionados", "Articulos seleccionados"
        INDIVIDUAL = "individual", "Un articulo"

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name="descuentos_promocionales",
    )
    codigo = models.CharField(max_length=80)
    titulo = models.CharField(max_length=160)
    descripcion = models.TextField(blank=True)
    alcance = models.CharField(max_length=20, choices=Alcance.choices)
    porcentaje = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(99)]
    )
    productos = models.ManyToManyField(
        Producto,
        through="DescuentoProducto",
        related_name="descuentos_promocionales",
        blank=True,
    )
    activo = models.BooleanField(default=True)
    fecha_inicio = models.DateTimeField(null=True, blank=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-porcentaje", "-fecha_creacion", "-id"]
        verbose_name = "descuento promocional"
        verbose_name_plural = "descuentos promocionales"
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "codigo"],
                name="descuento_codigo_unico_por_empresa",
            )
        ]
        indexes = [
            models.Index(fields=["empresa", "activo", "alcance"]),
            models.Index(fields=["empresa", "fecha_inicio", "fecha_fin"]),
        ]

    def __str__(self):
        return f"{self.empresa} - {self.titulo} ({self.porcentaje}%)"

    @property
    def esta_vigente(self):
        ahora = timezone.now()
        if not self.activo:
            return False
        if self.fecha_inicio and self.fecha_inicio > ahora:
            return False
        if self.fecha_fin and self.fecha_fin < ahora:
            return False
        return True

    @property
    def prioridad_alcance(self):
        return {
            self.Alcance.TODOS: 1,
            self.Alcance.SELECCIONADOS: 2,
            self.Alcance.INDIVIDUAL: 3,
        }[self.alcance]

    def clean(self):
        super().clean()
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            raise ValidationError(
                {"fecha_fin": "La fecha final no puede ser menor que la fecha inicial."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class DescuentoProducto(models.Model):
    descuento = models.ForeignKey(
        DescuentoPromocional,
        on_delete=models.CASCADE,
        related_name="items_productos",
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name="items_descuentos",
    )

    class Meta:
        ordering = ["producto__nombre", "producto_id"]
        verbose_name = "producto de descuento"
        verbose_name_plural = "productos de descuento"
        constraints = [
            models.UniqueConstraint(
                fields=["descuento", "producto"],
                name="descuento_producto_unico",
            )
        ]

    def __str__(self):
        return f"{self.descuento} - {self.producto}"

    def clean(self):
        super().clean()
        if self.descuento_id and self.producto_id:
            if self.descuento.empresa_id != self.producto.empresa_id:
                raise ValidationError(
                    {
                        "producto": (
                            "El producto debe pertenecer a la misma empresa "
                            "del descuento."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
