from rest_framework.permissions import BasePermission


class IsSuperUser(BasePermission):
    message = "Solo el superusuario puede administrar empresas."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_superuser
        )
