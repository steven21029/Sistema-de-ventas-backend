from rest_framework.permissions import BasePermission, SAFE_METHODS

from .models import PerfilUsuario


class IsAdministrativeUser(BasePermission):
    message = "No tienes acceso al panel administrativo."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True

        perfil = getattr(user, "perfil", None)
        return bool(
            perfil
            and perfil.activo
            and perfil.rol
            in [
                PerfilUsuario.Rol.ADMINISTRADOR_MAESTRO,
                PerfilUsuario.Rol.ADMINISTRADOR_EMPRESA,
                PerfilUsuario.Rol.GERENTE,
            ]
        )


class IsSuperUserOrReadOwnProfile(BasePermission):
    message = "Solo el superusuario puede administrar perfiles de usuario."

    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_superuser:
            return True

        return request.method in SAFE_METHODS and obj.usuario_id == request.user.id

    def has_permission(self, request, view):
        if request.user and request.user.is_superuser:
            return True

        return request.method in SAFE_METHODS
