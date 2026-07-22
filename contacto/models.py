from django.core.exceptions import ValidationError
from django.db import models

from empresas.models import Empresa


class MensajeContacto(models.Model):
    class Estado(models.TextChoices):
        NUEVO = "nuevo", "Nuevo"
        PENDIENTE = "pendiente", "Pendiente"
        RESPONDIDO = "respondido", "Respondido"
        CERRADO = "cerrado", "Cerrado"

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name="mensajes_contacto",
    )
    nombre = models.CharField(max_length=150)
    telefono = models.CharField(max_length=30, blank=True)
    correo = models.EmailField(blank=True)
    asunto = models.CharField(max_length=160, blank=True)
    mensaje = models.TextField()
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.NUEVO,
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion", "-id"]
        verbose_name = "mensaje de contacto"
        verbose_name_plural = "mensajes de contacto"
        indexes = [
            models.Index(fields=["empresa", "estado", "fecha_creacion"]),
        ]

    def __str__(self):
        return f"{self.empresa} - {self.nombre} - {self.estado}"

    def clean(self):
        super().clean()

        if not self.telefono and not self.correo:
            raise ValidationError(
                {"contacto": "Debes agregar telefono o correo para poder responder."}
            )
