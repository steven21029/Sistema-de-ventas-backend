from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.utils.text import slugify


hex_color_validator = RegexValidator(
    regex=r"^#[0-9A-Fa-f]{6}$",
    message="El color debe tener formato hexadecimal, por ejemplo #d1393d.",
)


class Empresa(models.Model):
    nombre = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    logo = models.ImageField(upload_to="empresas/logos/", blank=True, null=True)

    color_principal = models.CharField(
        max_length=7,
        default="#d1393d",
        validators=[hex_color_validator],
    )
    color_secundario = models.CharField(
        max_length=7,
        default="#e94a51",
        validators=[hex_color_validator],
    )
    color_acento = models.CharField(
        max_length=7,
        default="#2d4b77",
        validators=[hex_color_validator],
    )
    color_texto = models.CharField(
        max_length=7,
        default="#000000",
        validators=[hex_color_validator],
    )
    color_fondo = models.CharField(
        max_length=7,
        default="#ffffff",
        validators=[hex_color_validator],
    )

    telefono = models.CharField(max_length=30, blank=True)
    correo = models.EmailField(blank=True)
    direccion = models.TextField(blank=True)
    sitio_web = models.URLField(blank=True)

    activa = models.BooleanField(default=True)
    creada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="empresas_creadas",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "empresa"
        verbose_name_plural = "empresas"

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._generar_slug_unico()
        super().save(*args, **kwargs)

    def _generar_slug_unico(self):
        base_slug = slugify(self.nombre) or "empresa"
        slug = base_slug
        contador = 2

        while Empresa.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base_slug}-{contador}"
            contador += 1

        return slug
