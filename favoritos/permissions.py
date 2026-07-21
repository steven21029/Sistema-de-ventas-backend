from rest_framework.permissions import BasePermission


class IsFavoritoOwner(BasePermission):
    message = "No tienes permiso para administrar este favorito."

    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_superuser:
            return True

        return obj.usuario_id == request.user.id
