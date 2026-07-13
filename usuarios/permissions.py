from rest_framework.permissions import BasePermission, SAFE_METHODS


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
