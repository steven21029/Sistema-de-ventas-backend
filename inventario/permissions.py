from rest_framework.permissions import BasePermission

from usuarios.models import PerfilUsuario


class IsInventarioManager(BasePermission):
    message = "No tienes permiso para administrar inventario."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        perfil = getattr(request.user, "perfil", None)
        if not perfil or not perfil.activo:
            return False

        if perfil.es_administrador_maestro:
            return True

        return bool(
            perfil.empresa_id
            and perfil.rol
            in [
                PerfilUsuario.Rol.ADMINISTRADOR_EMPRESA,
                PerfilUsuario.Rol.GERENTE,
            ]
        )
