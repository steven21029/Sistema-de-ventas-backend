from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from catalogo.models import PaqueteCatalogo, Producto
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
        blank=True,
        null=True,
    )
    paquete = models.ForeignKey(
        PaqueteCatalogo,
        on_delete=models.PROTECT,
        related_name="favoritos",
        blank=True,
        null=True,
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
            ),
            models.UniqueConstraint(
                fields=["empresa", "usuario", "paquete"],
                name="favorito_unico_por_empresa_usuario_paquete",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(producto__isnull=False, paquete__isnull=True)
                    | models.Q(producto__isnull=True, paquete__isnull=False)
                ),
                name="favorito_un_solo_tipo_articulo",
            ),
        ]

    def __str__(self):
        return f"{self.usuario} - {self.articulo}"

    @property
    def articulo(self):
        return self.producto or self.paquete

    @property
    def tipo_articulo(self):
        if self.producto_id:
            return "producto"

        return self.paquete.tipo if self.paquete_id else None

    def clean(self):
        super().clean()
        if bool(self.producto_id) == bool(self.paquete_id):
            raise ValidationError(
                "El favorito debe tener un producto, perfil o combo, pero no varios."
            )

        if self.producto_id and self.empresa_id != self.producto.empresa_id:
            raise ValidationError(
                {"producto": "El producto debe pertenecer a la empresa del favorito."}
            )

        if self.paquete_id and self.empresa_id != self.paquete.empresa_id:
            raise ValidationError(
                {"paquete": "El perfil o combo debe pertenecer a la empresa del favorito."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
