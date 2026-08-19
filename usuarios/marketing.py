from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail

from .models import PerfilUsuario


CANALES_PROMOCIONALES = {"correo", "telefono"}


def perfiles_habilitados_para_promociones(empresa, canal):
    if canal not in CANALES_PROMOCIONALES:
        raise ValueError("El canal promocional no es valido.")

    perfiles = PerfilUsuario.objects.select_related("usuario", "empresa").filter(
        empresa=empresa,
        rol=PerfilUsuario.Rol.COMPRADOR,
        activo=True,
        acepta_promociones=True,
        fecha_aceptacion_promociones__isnull=False,
        fecha_retiro_promociones__isnull=True,
        usuario__is_active=True,
    )
    if canal == "correo":
        return perfiles.filter(
            correo_verificado=True,
        ).exclude(usuario__email="")
    return perfiles.exclude(telefono="")


def validar_comunicacion_promocional(usuario, canal):
    if canal not in CANALES_PROMOCIONALES:
        raise ValueError("El canal promocional no es valido.")

    perfil = getattr(usuario, "perfil", None)
    permitido = bool(
        perfil
        and usuario.is_active
        and perfil.activo
        and perfil.es_comprador
        and perfil.acepta_promociones
        and perfil.fecha_aceptacion_promociones
        and not perfil.fecha_retiro_promociones
    )
    if canal == "correo":
        permitido = permitido and perfil.correo_verificado and bool(usuario.email)
    else:
        permitido = permitido and bool(perfil.telefono)

    if not permitido:
        raise PermissionDenied(
            "El usuario no autorizo comunicaciones promocionales por este canal."
        )
    return perfil


def enviar_correo_promocional(*, usuario, asunto, mensaje, html_message=None):
    validar_comunicacion_promocional(usuario, "correo")
    return send_mail(
        subject=asunto,
        message=mensaje,
        from_email=None,
        recipient_list=[usuario.email],
        fail_silently=False,
        html_message=html_message,
    )
