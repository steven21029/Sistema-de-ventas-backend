from decimal import Decimal

from django.db.models import DecimalField, ExpressionWrapper, F, Q, Sum
from django.shortcuts import get_object_or_404
from rest_framework import generics, mixins, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from catalogo.models import Producto
from .models import MovimientoInventario
from .permissions import IsInventarioManager
from .serializers import (
    AjustarExistenciaSerializer,
    MovimientoInventarioSerializer,
    ProductoInventarioSerializer,
)


class InventarioEmpresaMixin:
    def filtrar_por_permiso(self, queryset):
        user = self.request.user
        empresa_slug = self._empresa_slug()

        if user.is_superuser:
            return self._filtrar_empresa_slug(queryset, empresa_slug)

        perfil = getattr(user, "perfil", None)
        if not perfil or not perfil.activo:
            return queryset.none()

        if perfil.es_administrador_maestro:
            return self._filtrar_empresa_slug(queryset, empresa_slug)

        if perfil.empresa_id:
            return queryset.filter(empresa=perfil.empresa)

        return queryset.none()

    def _empresa_slug(self):
        return (
            self.request.query_params.get("empresa_slug", "")
            or self.request.data.get("empresa_slug", "")
        ).strip()

    def _filtrar_empresa_slug(self, queryset, empresa_slug):
        if empresa_slug:
            return queryset.filter(empresa__slug__iexact=empresa_slug)

        return queryset


class ProductoInventarioQuerysetMixin(InventarioEmpresaMixin):
    serializer_class = ProductoInventarioSerializer
    permission_classes = [IsInventarioManager]

    def get_queryset(self):
        queryset = Producto.objects.select_related("empresa", "familia", "categoria")
        queryset = self.filtrar_por_permiso(queryset)
        return self.aplicar_filtros(queryset)

    def aplicar_filtros(self, queryset):
        buscar = self.request.query_params.get("buscar", "").strip()
        activo = self.request.query_params.get("activo", "").strip().lower()

        if buscar:
            queryset = queryset.filter(
                Q(nombre__icontains=buscar)
                | Q(codigo_barra__icontains=buscar)
                | Q(familia__nombre__icontains=buscar)
                | Q(categoria__nombre__icontains=buscar)
            )

        if activo in ["true", "1", "si", "yes"]:
            queryset = queryset.filter(activo=True)
        elif activo in ["false", "0", "no"]:
            queryset = queryset.filter(activo=False)

        return queryset.order_by("empresa__nombre", "nombre")


class ProductoInventarioListView(
    ProductoInventarioQuerysetMixin,
    generics.ListAPIView,
):
    pass


class ProductoBajoStockListView(
    ProductoInventarioQuerysetMixin,
    generics.ListAPIView,
):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(existencia__gt=0, existencia__lte=F("existencia_minima"))
        )


class ProductoAgotadoListView(
    ProductoInventarioQuerysetMixin,
    generics.ListAPIView,
):
    def get_queryset(self):
        return super().get_queryset().filter(existencia=0)


class ResumenInventarioView(InventarioEmpresaMixin, generics.GenericAPIView):
    permission_classes = [IsInventarioManager]

    def get(self, request, *args, **kwargs):
        queryset = Producto.objects.select_related("empresa")
        queryset = self.filtrar_por_permiso(queryset)

        valor_expression = ExpressionWrapper(
            F("existencia") * F("precio"),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )

        resumen = queryset.aggregate(
            existencia_total=Sum("existencia"),
            valor_inventario=Sum(valor_expression),
        )

        data = {
            "total_productos": queryset.count(),
            "productos_activos": queryset.filter(activo=True).count(),
            "productos_agotados": queryset.filter(activo=True, existencia=0).count(),
            "productos_bajo_stock": queryset.filter(
                activo=True,
                existencia__gt=0,
                existencia__lte=F("existencia_minima"),
            ).count(),
            "existencia_total": resumen["existencia_total"] or 0,
            "valor_inventario": resumen["valor_inventario"] or Decimal("0.00"),
        }

        return Response(data)


class AjustarExistenciaView(InventarioEmpresaMixin, generics.GenericAPIView):
    serializer_class = AjustarExistenciaSerializer
    permission_classes = [IsInventarioManager]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        producto = self._obtener_producto(serializer.validated_data["codigo_barra"])
        existencia_nueva = serializer.validated_data["existencia_nueva"]
        movimiento = MovimientoInventario.objects.create(
            empresa=producto.empresa,
            producto=producto,
            tipo=MovimientoInventario.Tipo.AJUSTE,
            cantidad=existencia_nueva,
            motivo=serializer.validated_data.get("motivo") or "Ajuste desde inventario",
            referencia=serializer.validated_data.get("referencia", ""),
            usuario=request.user,
        )
        producto.refresh_from_db()

        data = {
            "mensaje": "Existencia ajustada correctamente.",
            "producto": ProductoInventarioSerializer(
                producto,
                context=self.get_serializer_context(),
            ).data,
            "movimiento": MovimientoInventarioSerializer(
                movimiento,
                context=self.get_serializer_context(),
            ).data,
        }

        return Response(data, status=status.HTTP_201_CREATED)

    def _obtener_producto(self, codigo_barra):
        queryset = Producto.objects.select_related("empresa", "familia", "categoria")
        queryset = self.filtrar_por_permiso(queryset).filter(codigo_barra=codigo_barra)

        if queryset.count() > 1:
            raise ValidationError(
                {
                    "empresa_slug": (
                        "Hay mas de una empresa con este codigo de barra. "
                        "Envia empresa_slug para elegir una."
                    )
                }
            )

        return get_object_or_404(queryset)

class MovimientoInventarioViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = MovimientoInventarioSerializer
    permission_classes = [IsInventarioManager]

    def get_queryset(self):
        queryset = MovimientoInventario.objects.select_related(
            "empresa",
            "producto",
            "usuario",
        )
        empresa_slug = self.request.query_params.get("empresa_slug", "").strip()

        if self.request.user.is_superuser:
            if empresa_slug:
                return queryset.filter(empresa__slug__iexact=empresa_slug)
            return queryset

        perfil = getattr(self.request.user, "perfil", None)
        if perfil and perfil.activo and perfil.es_administrador_maestro:
            if empresa_slug:
                return queryset.filter(empresa__slug__iexact=empresa_slug)
            return queryset

        if perfil and perfil.empresa_id:
            return queryset.filter(empresa=perfil.empresa)

        return queryset.none()

    def perform_create(self, serializer):
        perfil = getattr(self.request.user, "perfil", None)
        if self.request.user.is_superuser or (
            perfil and perfil.es_administrador_maestro
        ):
            serializer.save(usuario=self.request.user)
            return

        serializer.save(
            empresa=self.request.user.perfil.empresa,
            usuario=self.request.user,
        )
