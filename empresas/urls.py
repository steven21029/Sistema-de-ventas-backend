from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    EmpresaActualView,
    EmpresaMenuView,
    EmpresaPublicaView,
    EmpresaViewSet,
    SucursalEmpresaListView,
)

router = DefaultRouter()
router.register("empresas", EmpresaViewSet, basename="empresas")

urlpatterns = [
    path("empresas/actual/", EmpresaActualView.as_view(), name="empresas-actual"),
    path("empresas/menu/", EmpresaMenuView.as_view(), name="empresas-menu"),
    path("empresas/publica/", EmpresaPublicaView.as_view(), name="empresas-publica"),
    path(
        "empresas/sucursales/",
        SucursalEmpresaListView.as_view(),
        name="empresas-sucursales",
    ),
    path("", include(router.urls)),
]
