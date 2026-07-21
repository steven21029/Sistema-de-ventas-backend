from rest_framework.permissions import SAFE_METHODS, BasePermission

from usuarios.models import PerfilUsuario


class IsCatalogoManagerOrReadOnly(BasePermission):
    message = "No tienes permiso para administrar el catalogo."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        perfil = getattr(request.user, "perfil", None)
        return bool(
            perfil
            and perfil.activo
            and perfil.empresa_id
            and perfil.rol
            in [
                PerfilUsuario.Rol.ADMINISTRADOR_MAESTRO,
                PerfilUsuario.Rol.GERENTE,
            ]
        )
