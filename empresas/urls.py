from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    DepartamentoViewSet,
    EmpresaActualView,
    EmpresaMenuView,
    EmpresaPublicaView,
    EmpresaViewSet,
    ContextoAdministrativoView,
    ItemMenuEmpresaViewSet,
    MiEmpresaView,
    MiSobreNosotrosEmpresaView,
    MunicipioViewSet,
    SobreNosotrosEmpresaPublicoView,
    SucursalesCercanasView,
    SucursalesZonasView,
    SucursalEmpresaViewSet,
)

router = DefaultRouter()
router.register(
    "empresas/items-menu",
    ItemMenuEmpresaViewSet,
    basename="empresas-items-menu",
)
router.register("empresas", EmpresaViewSet, basename="empresas")

sucursales_lista = SucursalEmpresaViewSet.as_view(
    {"get": "list", "post": "create"}
)
sucursales_detalle = SucursalEmpresaViewSet.as_view(
    {
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
        "delete": "destroy",
    }
)
departamentos_lista = DepartamentoViewSet.as_view({"get": "list", "post": "create"})
departamentos_detalle = DepartamentoViewSet.as_view(
    {
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
        "delete": "destroy",
    }
)
municipios_lista = MunicipioViewSet.as_view({"get": "list", "post": "create"})
municipios_detalle = MunicipioViewSet.as_view(
    {
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
        "delete": "destroy",
    }
)

urlpatterns = [
    path("empresas/actual/", EmpresaActualView.as_view(), name="empresas-actual"),
    path("empresas/menu/", EmpresaMenuView.as_view(), name="empresas-menu"),
    path("empresas/publica/", EmpresaPublicaView.as_view(), name="empresas-publica"),
    path(
        "empresas/sobre-nosotros/",
        SobreNosotrosEmpresaPublicoView.as_view(),
        name="empresas-sobre-nosotros",
    ),
    path(
        "empresas/mi-empresa/",
        MiEmpresaView.as_view(),
        name="empresas-mi-empresa",
    ),
    path(
        "empresas/contexto-administrativo/",
        ContextoAdministrativoView.as_view(),
        name="empresas-contexto-administrativo",
    ),
    path(
        "empresas/mi-sobre-nosotros/",
        MiSobreNosotrosEmpresaView.as_view(),
        name="empresas-mi-sobre-nosotros",
    ),
    path(
        "ubicaciones/departamentos/",
        departamentos_lista,
        name="ubicaciones-departamentos",
    ),
    path(
        "ubicaciones/departamentos/<int:pk>/",
        departamentos_detalle,
        name="ubicaciones-departamentos-detalle",
    ),
    path(
        "ubicaciones/municipios/",
        municipios_lista,
        name="ubicaciones-municipios",
    ),
    path(
        "ubicaciones/municipios/<int:pk>/",
        municipios_detalle,
        name="ubicaciones-municipios-detalle",
    ),
    path(
        "empresas/sucursales/zonas/",
        SucursalesZonasView.as_view(),
        name="empresas-sucursales-zonas",
    ),
    path(
        "empresas/sucursales/cerca/",
        SucursalesCercanasView.as_view(),
        name="empresas-sucursales-cerca",
    ),
    path(
        "empresas/sucursales/",
        sucursales_lista,
        name="empresas-sucursales",
    ),
    path(
        "empresas/sucursales/<int:pk>/",
        sucursales_detalle,
        name="empresas-sucursales-detalle",
    ),
    path("", include(router.urls)),
]
