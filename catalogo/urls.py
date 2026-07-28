from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CategoriaViewSet,
    CombosDestacadosListView,
    ExamenesListView,
    FamiliaViewSet,
    PerfilesListView,
    ProductoViewSet,
    ProductosMasVendidosListView,
    ServicioDetallePublicoView,
    ServiciosListView,
)

router = DefaultRouter()
router.register("catalogo/familias", FamiliaViewSet, basename="catalogo-familias")
router.register("catalogo/categorias", CategoriaViewSet, basename="catalogo-categorias")
router.register("catalogo/productos", ProductoViewSet, basename="catalogo-productos")

urlpatterns = [
    path(
        "catalogo/combos-destacados/",
        CombosDestacadosListView.as_view(),
        name="catalogo-combos-destacados",
    ),
    path(
        "catalogo/productos-mas-vendidos/",
        ProductosMasVendidosListView.as_view(),
        name="catalogo-productos-mas-vendidos",
    ),
    path("catalogo/examenes/", ExamenesListView.as_view(), name="catalogo-examenes"),
    path("catalogo/perfiles/", PerfilesListView.as_view(), name="catalogo-perfiles"),
    path("catalogo/servicios/", ServiciosListView.as_view(), name="catalogo-servicios"),
    path(
        "catalogo/servicios/detalle/",
        ServicioDetallePublicoView.as_view(),
        name="catalogo-servicio-detalle",
    ),
    path("", include(router.urls)),
]
