from rest_framework.permissions import BasePermission

from usuarios.models import PerfilUsuario


class IsPedidoOwnerOrEmpresaManager(BasePermission):
    message = "No tienes permiso para administrar este recurso."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_superuser:
            return True

        perfil = getattr(user, "perfil", None)
        if not perfil or not perfil.activo or not perfil.empresa_id:
            return False

        empresa_id, usuario_id = self._resolver_empresa_usuario(obj)
        if empresa_id != perfil.empresa_id:
            return False

        if perfil.es_gerente:
            return True

        return usuario_id == user.id

    def _resolver_empresa_usuario(self, obj):
        if hasattr(obj, "carrito"):
            return obj.carrito.empresa_id, obj.carrito.usuario_id

        if hasattr(obj, "pedido"):
            return obj.pedido.empresa_id, obj.pedido.usuario_id

        return obj.empresa_id, obj.usuario_id


class IsTarifaEntregaAdmin(BasePermission):
    message = "No tienes permiso para administrar tarifas de entrega."

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
                or (perfil.es_administrador_empresa and perfil.empresa_id)
            )
        )

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_superuser:
            return True

        perfil = getattr(user, "perfil", None)
        if not perfil or not perfil.activo:
            return False

        if perfil.es_administrador_maestro:
            return True

        return bool(
            perfil.es_administrador_empresa
            and perfil.empresa_id
            and obj.empresa_id == perfil.empresa_id
        )
