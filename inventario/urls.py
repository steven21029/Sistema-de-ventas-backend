from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import MovimientoInventarioViewSet

router = DefaultRouter()
router.register(
    "inventario/movimientos",
    MovimientoInventarioViewSet,
    basename="inventario-movimientos",
)

urlpatterns = [
    path("", include(router.urls)),
]
