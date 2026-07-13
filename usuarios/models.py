from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from empresas.models import Empresa


class PerfilUsuario(models.Model):
    class Rol(models.TextChoices):
        ADMINISTRADOR_MAESTRO = "administrador_maestro", "Administrador maestro"
        GERENTE = "gerente", "Gerente"
        COMPRADOR = "comprador", "Comprador"

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="perfil",
    )
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="perfiles_usuario",
    )
    rol = models.CharField(
        max_length=30,
        choices=Rol.choices,
        default=Rol.COMPRADOR,
    )
    telefono = models.CharField(max_length=30, blank=True)
    correo_verificado = models.BooleanField(default=False)
    puede_crear_usuarios = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["usuario__username"]
        verbose_name = "perfil de usuario"
        verbose_name_plural = "perfiles de usuario"

    def __str__(self):
        return f"{self.usuario} - {self.get_rol_display()}"

    def clean(self):
        super().clean()
        if self.rol != self.Rol.ADMINISTRADOR_MAESTRO and not self.empresa_id:
            raise ValidationError(
                {"empresa": "Los gerentes y compradores deben pertenecer a una empresa."}
            )

    @property
    def es_administrador_maestro(self):
        return self.rol == self.Rol.ADMINISTRADOR_MAESTRO

    @property
    def es_gerente(self):
        return self.rol == self.Rol.GERENTE

    @property
    def es_comprador(self):
        return self.rol == self.Rol.COMPRADOR
