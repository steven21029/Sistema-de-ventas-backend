from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from empresas.contexto import obtener_empresa_administrable
from usuarios.permissions import IsAdministrativeUser

from .serializers import (
    ExportarVentasParametrosSerializer,
    ResumenVentasParametrosSerializer,
)
from .services import (
    ReporteVentasService,
    exportar_csv,
    exportar_pdf,
    exportar_xlsx,
)


class ReporteAdministrativoAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdministrativeUser]

    def obtener_empresa(self, request, empresa_slug):
        empresa = obtener_empresa_administrable(request)
        if empresa.slug.lower() != empresa_slug.lower():
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("No puedes consultar reportes de otra empresa.")
        return empresa


class ResumenVentasView(ReporteAdministrativoAPIView):
    def get(self, request):
        entrada = ResumenVentasParametrosSerializer(data=request.query_params)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data
        empresa = self.obtener_empresa(request, datos["empresa_slug"])
        servicio = ReporteVentasService(
            empresa=empresa,
            fecha_desde=datos["fecha_desde"],
            fecha_hasta=datos["fecha_hasta"],
            agrupacion=datos["agrupacion"],
        )
        return Response(
            servicio.construir_resumen(
                comparar_periodo_anterior=datos["comparar_periodo_anterior"]
            )
        )


class ExportarVentasView(ReporteAdministrativoAPIView):
    EXPORTADORES = {
        "csv": (exportar_csv, "text/csv; charset=utf-8"),
        "xlsx": (
            exportar_xlsx,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
        "pdf": (exportar_pdf, "application/pdf"),
    }

    def get(self, request):
        entrada = ExportarVentasParametrosSerializer(data=request.query_params)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data
        empresa = self.obtener_empresa(request, datos["empresa_slug"])
        servicio = ReporteVentasService(
            empresa=empresa,
            fecha_desde=datos["fecha_desde"],
            fecha_hasta=datos["fecha_hasta"],
        )
        tabla = servicio.construir_tabla(datos["tipo"])
        exportador, content_type = self.EXPORTADORES[datos["formato"]]
        contenido = exportador(tabla)
        nombre = (
            f"reporte_{datos['tipo']}_{empresa.slug}_"
            f"{datos['fecha_desde'].isoformat()}_{datos['fecha_hasta'].isoformat()}."
            f"{datos['formato']}"
        )
        respuesta = HttpResponse(contenido, content_type=content_type)
        respuesta["Content-Disposition"] = f'attachment; filename="{nombre}"'
        return respuesta
