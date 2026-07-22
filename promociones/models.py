from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

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
    url_boton = models.URLField(blank=True)
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
