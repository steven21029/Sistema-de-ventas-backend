from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AjustarExistenciaView,
    MovimientoInventarioViewSet,
    ProductoAgotadoListView,
    ProductoBajoStockListView,
    ProductoInventarioListView,
    ResumenInventarioView,
)

router = DefaultRouter()
router.register(
    "inventario/movimientos",
    MovimientoInventarioViewSet,
    basename="inventario-movimientos",
)

urlpatterns = [
    path("inventario/resumen/", ResumenInventarioView.as_view(), name="inventario-resumen"),
    path("inventario/productos/", ProductoInventarioListView.as_view(), name="inventario-productos"),
    path(
        "inventario/productos-bajo-stock/",
        ProductoBajoStockListView.as_view(),
        name="inventario-productos-bajo-stock",
    ),
    path(
        "inventario/productos-agotados/",
        ProductoAgotadoListView.as_view(),
        name="inventario-productos-agotados",
    ),
    path(
        "inventario/ajustar-existencia/",
        AjustarExistenciaView.as_view(),
        name="inventario-ajustar-existencia",
    ),
    path("", include(router.urls)),
]
