from rest_framework.permissions import SAFE_METHODS, BasePermission

from usuarios.models import PerfilUsuario


class IsBannerPromocionalAdminOrReadOnly(BasePermission):
    message = "No tienes permiso para administrar banners promocionales."

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
            and (
                perfil.es_administrador_maestro
                or perfil.es_administrador_empresa
                or perfil.es_gerente
            )
        )

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        if request.user.is_superuser:
            return True

        perfil = getattr(request.user, "perfil", None)
        if not perfil or not perfil.activo:
            return False

        if perfil.es_administrador_maestro:
            return True

        return bool(
            perfil.rol
            in [
                PerfilUsuario.Rol.ADMINISTRADOR_EMPRESA,
                PerfilUsuario.Rol.GERENTE,
            ]
            and perfil.empresa_id == obj.empresa_id
        )
