from django.urls import path

from .views import ExportarVentasView, ResumenVentasView


urlpatterns = [
    path(
        "reportes/resumen-ventas/",
        ResumenVentasView.as_view(),
        name="reportes-resumen-ventas",
    ),
    path(
        "reportes/ventas/exportar/",
        ExportarVentasView.as_view(),
        name="reportes-ventas-exportar",
    ),
]
