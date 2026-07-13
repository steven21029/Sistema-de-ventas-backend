from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PerfilUsuarioViewSet

router = DefaultRouter()
router.register("usuarios/perfiles", PerfilUsuarioViewSet, basename="usuarios-perfiles")

urlpatterns = [
    path("", include(router.urls)),
]
