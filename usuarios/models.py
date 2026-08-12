import logging
import secrets

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

from empresas.models import Empresa, Municipio


numero_identidad_validator = RegexValidator(
    regex=r"^\d{13}$",
    message="El numero de identidad debe tener exactamente 13 digitos.",
)
telefono_validator = RegexValidator(
    regex=r"^\d+$",
    message="El telefono solo debe contener numeros.",
)


logger = logging.getLogger(__name__)


class ErrorEnvioCodigoCorreo(Exception):
    pass


class PerfilUsuario(models.Model):
    class Rol(models.TextChoices):
        ADMINISTRADOR_MAESTRO = "administrador_maestro", "Administrador maestro"
        ADMINISTRADOR_EMPRESA = "administrador_empresa", "Administrador de empresa"
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
    municipio = models.ForeignKey(
        Municipio,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="perfiles_usuario",
    )
    empresas_permitidas = models.ManyToManyField(
        Empresa,
        blank=True,
        related_name="administradores_maestros_permitidos",
        help_text=(
            "Empresas que puede administrar un administrador maestro. "
            "Los superusuarios no requieren esta asignacion."
        ),
    )
    rol = models.CharField(
        max_length=30,
        choices=Rol.choices,
        default=Rol.COMPRADOR,
    )
    telefono = models.CharField(
        max_length=30,
        blank=True,
        validators=[telefono_validator],
    )
    numero_identidad = models.CharField(
        max_length=13,
        blank=True,
        default="",
        validators=[numero_identidad_validator],
        help_text="Numero de identidad hondureno de 13 digitos.",
    )
    correo_verificado = models.BooleanField(default=False)
    puede_crear_usuarios = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["usuario__username"]
        verbose_name = "perfil de usuario"
        verbose_name_plural = "perfiles de usuario"
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "numero_identidad"],
                condition=(
                    models.Q(empresa__isnull=False)
                    & ~models.Q(numero_identidad="")
                ),
                name="perfil_identidad_unica_por_empresa",
            ),
        ]

    def __str__(self):
        return f"{self.usuario} - {self.get_rol_display()}"

    def clean(self):
        super().clean()
        if self.numero_identidad and not self.numero_identidad.isdigit():
            raise ValidationError(
                {"numero_identidad": "El numero de identidad solo debe contener numeros."}
            )

        if self.rol != self.Rol.ADMINISTRADOR_MAESTRO and not self.empresa_id:
            raise ValidationError(
                {
                    "empresa": (
                        "Los administradores de empresa, gerentes y compradores "
                        "deben pertenecer a una empresa."
                    )
                }
            )

    @property
    def es_administrador_maestro(self):
        return self.rol == self.Rol.ADMINISTRADOR_MAESTRO

    @property
    def es_administrador_empresa(self):
        return self.rol == self.Rol.ADMINISTRADOR_EMPRESA

    @property
    def es_gerente(self):
        return self.rol == self.Rol.GERENTE

    @property
    def es_comprador(self):
        return self.rol == self.Rol.COMPRADOR

    @property
    def departamento(self):
        if not self.municipio_id:
            return None
        return self.municipio.departamento


class CodigoVerificacionCorreo(models.Model):
    class Tipo(models.TextChoices):
        VERIFICACION_CORREO = "verificacion_correo", "Verificacion de correo"
        RECUPERACION_CONTRASENA = (
            "recuperacion_contrasena",
            "Recuperacion de contrasena",
        )

    LONGITUD_CODIGO = 6
    DURACION_MINUTOS = 15
    MAX_INTENTOS = 5
    ESPERA_REENVIO_SEGUNDOS = 60

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="codigos_verificacion_correo",
    )
    codigo = models.CharField(max_length=6)
    tipo = models.CharField(
        max_length=30,
        choices=Tipo.choices,
        default=Tipo.VERIFICACION_CORREO,
    )
    usado = models.BooleanField(default=False)
    intentos = models.PositiveSmallIntegerField(default=0)
    fecha_expiracion = models.DateTimeField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_uso = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-fecha_creacion"]
        verbose_name = "codigo de verificacion de correo"
        verbose_name_plural = "codigos de verificacion de correo"
        indexes = [
            models.Index(fields=["usuario", "tipo", "usado"]),
        ]

    def __str__(self):
        return f"{self.usuario} - {self.get_tipo_display()}"

    @classmethod
    def generar_codigo(cls):
        limite = 10**cls.LONGITUD_CODIGO
        return f"{secrets.randbelow(limite):0{cls.LONGITUD_CODIGO}d}"

    @classmethod
    def crear_para_usuario(cls, usuario, tipo=Tipo.VERIFICACION_CORREO):
        cls.objects.filter(
            usuario=usuario,
            tipo=tipo,
            usado=False,
        ).update(usado=True)

        return cls.objects.create(
            usuario=usuario,
            codigo=cls.generar_codigo(),
            tipo=tipo,
            fecha_expiracion=timezone.now()
            + timezone.timedelta(minutes=cls.DURACION_MINUTOS),
        )

    @property
    def expirado(self):
        return timezone.now() >= self.fecha_expiracion

    @property
    def puede_usarse(self):
        return not self.usado and not self.expirado and self.intentos < self.MAX_INTENTOS

    def registrar_intento_fallido(self):
        self.intentos += 1
        if self.intentos >= self.MAX_INTENTOS:
            self.usado = True
        self.save(update_fields=["intentos", "usado"])

    def marcar_como_usado(self):
        self.usado = True
        self.fecha_uso = timezone.now()
        self.save(update_fields=["usado", "fecha_uso"])

    def enviar_por_correo(self):
        if self.tipo == self.Tipo.RECUPERACION_CONTRASENA:
            subject = "Tu codigo para recuperar contrasena"
            message = (
                f"Tu codigo para recuperar contrasena es: {self.codigo}\n\n"
                f"Este codigo vence en {self.DURACION_MINUTOS} minutos."
            )
        else:
            subject = "Tu codigo de verificacion"
            message = (
                f"Tu codigo de verificacion es: {self.codigo}\n\n"
                f"Este codigo vence en {self.DURACION_MINUTOS} minutos."
            )

        try:
            enviados = send_mail(
                subject=subject,
                message=message,
                from_email=None,
                recipient_list=[self.usuario.email],
                fail_silently=False,
            )
        except Exception as exc:
            logger.exception(
                "El proveedor rechazo el correo de codigo para el usuario %s.",
                self.usuario_id,
            )
            raise ErrorEnvioCodigoCorreo(
                "No fue posible enviar el codigo de verificacion."
            ) from exc
        if enviados != 1:
            raise ErrorEnvioCodigoCorreo(
                "El proveedor de correo no confirmo el envio del codigo."
            )
        logger.info(
            "Correo de codigo aceptado por el proveedor para el usuario %s.",
            self.usuario_id,
        )
        return enviados
