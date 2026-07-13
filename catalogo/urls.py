from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CategoriaViewSet, FamiliaViewSet, ProductoViewSet

router = DefaultRouter()
router.register("catalogo/familias", FamiliaViewSet, basename="catalogo-familias")
router.register("catalogo/categorias", CategoriaViewSet, basename="catalogo-categorias")
router.register("catalogo/productos", ProductoViewSet, basename="catalogo-productos")

urlpatterns = [
    path("", include(router.urls)),
]
