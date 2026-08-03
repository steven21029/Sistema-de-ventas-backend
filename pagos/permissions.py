from rest_framework.permissions import BasePermission

from empresas.contexto import empresas_administrables


class IsPagoOwnerOrEmpresaStaff(BasePermission):
    message = "No tienes permiso para consultar este pago."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_superuser:
            return True

        perfil = getattr(user, "perfil", None)
        if not perfil or not perfil.activo:
            return False
        if perfil.es_administrador_maestro:
            return empresas_administrables(user).filter(pk=obj.empresa_id).exists()
        if not perfil.empresa_id or obj.empresa_id != perfil.empresa_id:
            return False
        if perfil.es_administrador_empresa or perfil.es_gerente:
            return True
        return obj.usuario_id == user.id
