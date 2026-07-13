from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
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
    precio = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    existencia = models.PositiveIntegerField(default=0)
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
    def agotado(self):
        return self.existencia == 0
