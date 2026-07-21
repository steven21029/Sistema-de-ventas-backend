from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from catalogo.models import Producto
from empresas.models import Empresa


class Favorito(models.Model):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name="favoritos",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favoritos",
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name="favoritos",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha_creacion", "-id"]
        verbose_name = "favorito"
        verbose_name_plural = "favoritos"
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "usuario", "producto"],
                name="favorito_unico_por_empresa_usuario_producto",
            )
        ]

    def __str__(self):
        return f"{self.usuario} - {self.producto}"

    def clean(self):
        super().clean()
        if self.producto_id and self.empresa_id != self.producto.empresa_id:
            raise ValidationError(
                {"producto": "El producto debe pertenecer a la empresa del favorito."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
