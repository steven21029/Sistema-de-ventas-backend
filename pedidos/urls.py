from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CalcularCarritoPublicoView,
    CarritoViewSet,
    DetallePedidoViewSet,
    ItemCarritoViewSet,
    PedidoViewSet,
    TarifaEntregaViewSet,
)

router = DefaultRouter()
router.register("pedidos/carritos", CarritoViewSet, basename="pedidos-carritos")
router.register("pedidos/items-carrito", ItemCarritoViewSet, basename="pedidos-items-carrito")
router.register("pedidos/pedidos", PedidoViewSet, basename="pedidos-pedidos")
router.register("pedidos/detalles", DetallePedidoViewSet, basename="pedidos-detalles")
router.register("pedidos/tarifas-entrega", TarifaEntregaViewSet, basename="pedidos-tarifas-entrega")

urlpatterns = [
    path(
        "pedidos/carrito/calcular/",
        CalcularCarritoPublicoView.as_view(),
        name="pedidos-carrito-calcular",
    ),
    path("", include(router.urls)),
]
