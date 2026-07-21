from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import decorators, response, status, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import Carrito, DetallePedido, ItemCarrito, Pedido, Prefactura, TarifaEntrega
from .permissions import IsPedidoOwnerOrEmpresaManager, IsTarifaEntregaAdmin
from .serializers import (
    CarritoSerializer,
    DetallePedidoSerializer,
    GenerarPedidoDesdeCarritoSerializer,
    ItemCarritoSerializer,
    PedidoSerializer,
    PrefacturaSerializer,
    TarifaEntregaSerializer,
)


class EmpresaUsuarioMixin:
    def get_empresa_usuario(self):
        perfil = getattr(self.request.user, "perfil", None)
        if not perfil or not perfil.empresa_id:
            raise PermissionDenied("El usuario no tiene una empresa asignada.")

        return perfil.empresa


class CarritoViewSet(EmpresaUsuarioMixin, viewsets.ModelViewSet):
    serializer_class = CarritoSerializer
    permission_classes = [IsPedidoOwnerOrEmpresaManager]

    def get_queryset(self):
        queryset = Carrito.objects.select_related("empresa", "usuario").prefetch_related("items")

        if self.request.user.is_superuser:
            return queryset

        empresa = self.get_empresa_usuario()
        if self.request.user.perfil.es_gerente:
            return queryset.filter(empresa=empresa)

        return queryset.filter(empresa=empresa, usuario=self.request.user)

    def perform_create(self, serializer):
        if self.request.user.is_superuser:
            serializer.save()
            return

        serializer.save(empresa=self.get_empresa_usuario(), usuario=self.request.user)

    @decorators.action(detail=True, methods=["post"], url_path="generar-pedido")
    def generar_pedido(self, request, pk=None):
        carrito = self.get_object()
        entrada_serializer = GenerarPedidoDesdeCarritoSerializer(data=request.data)
        entrada_serializer.is_valid(raise_exception=True)

        try:
            pedido = Pedido.generar_desde_carrito(
                carrito=carrito,
                tipo_entrega=entrada_serializer.validated_data["tipo_entrega"],
                observaciones=entrada_serializer.validated_data.get("observaciones", ""),
            )
        except DjangoValidationError as exc:
            raise ValidationError(self._normalizar_error_django(exc)) from exc

        salida_serializer = PedidoSerializer(pedido, context=self.get_serializer_context())
        return response.Response(salida_serializer.data, status=status.HTTP_201_CREATED)

    def _normalizar_error_django(self, error):
        if hasattr(error, "message_dict"):
            return error.message_dict

        return {"detail": error.messages}


class ItemCarritoViewSet(viewsets.ModelViewSet):
    serializer_class = ItemCarritoSerializer
    permission_classes = [IsPedidoOwnerOrEmpresaManager]

    def get_queryset(self):
        queryset = ItemCarrito.objects.select_related(
            "carrito",
            "carrito__empresa",
            "carrito__usuario",
            "producto",
        )

        if self.request.user.is_superuser:
            return queryset

        perfil = getattr(self.request.user, "perfil", None)
        if not perfil or not perfil.empresa_id:
            return queryset.none()

        if perfil.es_gerente:
            return queryset.filter(carrito__empresa=perfil.empresa)

        return queryset.filter(carrito__empresa=perfil.empresa, carrito__usuario=self.request.user)


class PedidoViewSet(EmpresaUsuarioMixin, viewsets.ModelViewSet):
    serializer_class = PedidoSerializer
    permission_classes = [IsPedidoOwnerOrEmpresaManager]

    def get_queryset(self):
        queryset = Pedido.objects.select_related("empresa", "usuario", "carrito_origen").prefetch_related("detalles")

        if self.request.user.is_superuser:
            return queryset

        empresa = self.get_empresa_usuario()
        if self.request.user.perfil.es_gerente:
            return queryset.filter(empresa=empresa)

        return queryset.filter(empresa=empresa, usuario=self.request.user)

    def perform_create(self, serializer):
        if self.request.user.is_superuser:
            serializer.save()
            return

        empresa = self.get_empresa_usuario()
        serializer.validated_data["empresa"] = empresa
        serializer.validate(serializer.validated_data)
        serializer.save(empresa=empresa, usuario=self.request.user)

    @decorators.action(detail=True, methods=["get"], url_path="prefactura")
    def prefactura(self, request, pk=None):
        pedido = self.get_object()

        if pedido.estado_pago != Pedido.EstadoPago.PAGADO:
            raise ValidationError(
                {"pedido": "La prefactura solo esta disponible para pedidos pagados."}
            )

        prefactura = Prefactura.obtener_o_crear_para_pedido(pedido)
        serializer = PrefacturaSerializer(prefactura)
        return response.Response(serializer.data)


class DetallePedidoViewSet(viewsets.ModelViewSet):
    serializer_class = DetallePedidoSerializer
    permission_classes = [IsPedidoOwnerOrEmpresaManager]

    def get_queryset(self):
        queryset = DetallePedido.objects.select_related(
            "pedido",
            "pedido__empresa",
            "pedido__usuario",
            "producto",
        )

        if self.request.user.is_superuser:
            return queryset

        perfil = getattr(self.request.user, "perfil", None)
        if not perfil or not perfil.empresa_id:
            return queryset.none()

        if perfil.es_gerente:
            return queryset.filter(pedido__empresa=perfil.empresa)

        return queryset.filter(pedido__empresa=perfil.empresa, pedido__usuario=self.request.user)


class TarifaEntregaViewSet(viewsets.ModelViewSet):
    serializer_class = TarifaEntregaSerializer
    permission_classes = [IsTarifaEntregaAdmin]

    def get_queryset(self):
        queryset = TarifaEntrega.objects.select_related("empresa")

        if self.request.user.is_superuser:
            return queryset

        perfil = getattr(self.request.user, "perfil", None)
        if not perfil or not perfil.activo:
            return queryset.none()

        if perfil.es_administrador_maestro:
            return queryset

        if perfil.es_administrador_empresa and perfil.empresa_id:
            return queryset.filter(empresa=perfil.empresa)

        return queryset.none()

    def perform_create(self, serializer):
        if self.request.user.is_superuser:
            serializer.save()
            return

        perfil = self.request.user.perfil
        if perfil.es_administrador_maestro:
            serializer.save()
            return

        serializer.save(empresa=perfil.empresa)

    def perform_update(self, serializer):
        if self.request.user.is_superuser:
            serializer.save()
            return

        perfil = self.request.user.perfil
        if perfil.es_administrador_maestro:
            serializer.save()
            return

        serializer.save(empresa=perfil.empresa)
