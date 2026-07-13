from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction

from catalogo.models import Producto
from empresas.models import Empresa


class MovimientoInventario(models.Model):
    class Tipo(models.TextChoices):
        ENTRADA = "entrada", "Entrada"
        SALIDA = "salida", "Salida"
        AJUSTE = "ajuste", "Ajuste"

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name="movimientos_inventario",
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name="movimientos_inventario",
    )
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    cantidad = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="En ajustes, la cantidad representa la existencia final contada.",
    )
    existencia_anterior = models.PositiveIntegerField(editable=False)
    existencia_nueva = models.PositiveIntegerField(editable=False)
    motivo = models.TextField(blank=True)
    referencia = models.CharField(max_length=120, blank=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimientos_inventario",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha_creacion", "-id"]
        verbose_name = "movimiento de inventario"
        verbose_name_plural = "movimientos de inventario"

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.producto} - {self.cantidad}"

    def clean(self):
        super().clean()

        if self.producto_id and self.empresa_id != self.producto.empresa_id:
            raise ValidationError(
                {"producto": "El producto debe pertenecer a la misma empresa del movimiento."}
            )

        if self.pk:
            return

        if self.tipo == self.Tipo.SALIDA and self.producto_id:
            if self.cantidad > self.producto.existencia:
                raise ValidationError(
                    {"cantidad": "No se puede registrar una salida mayor a la existencia actual."}
                )

    def save(self, *args, **kwargs):
        if self.pk:
            super().save(*args, **kwargs)
            return

        with transaction.atomic():
            producto = Producto.objects.select_for_update().get(pk=self.producto_id)
            self.existencia_anterior = producto.existencia
            self.existencia_nueva = self._calcular_existencia_nueva(producto.existencia)

            if self.existencia_nueva < 0:
                raise ValidationError(
                    {"cantidad": "La existencia no puede quedar en negativo."}
                )

            super().save(*args, **kwargs)

            producto.existencia = self.existencia_nueva
            producto.save(update_fields=["existencia", "fecha_actualizacion"])

    def _calcular_existencia_nueva(self, existencia_actual):
        if self.tipo == self.Tipo.ENTRADA:
            return existencia_actual + self.cantidad

        if self.tipo == self.Tipo.SALIDA:
            return existencia_actual - self.cantidad

        if self.tipo == self.Tipo.AJUSTE:
            return self.cantidad

        raise ValidationError({"tipo": "Tipo de movimiento no valido."})
