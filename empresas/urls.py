from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import EmpresaPublicaView, EmpresaViewSet

router = DefaultRouter()
router.register("empresas", EmpresaViewSet, basename="empresas")

urlpatterns = [
    path("empresas/publica/", EmpresaPublicaView.as_view(), name="empresas-publica"),
    path("", include(router.urls)),
]
