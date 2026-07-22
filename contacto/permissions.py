from rest_framework.permissions import BasePermission

from usuarios.models import PerfilUsuario


class IsMensajeContactoAdmin(BasePermission):
    message = "No tienes permiso para administrar mensajes de contacto."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        perfil = getattr(request.user, "perfil", None)
        return bool(
            perfil
            and perfil.activo
            and (
                perfil.es_administrador_maestro
                or perfil.rol
                in [
                    PerfilUsuario.Rol.ADMINISTRADOR_EMPRESA,
                    PerfilUsuario.Rol.GERENTE,
                ]
            )
        )
