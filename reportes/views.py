from django.http import HttpResponse
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from empresas.contexto import obtener_empresa_administrable
from empresas.models import SucursalEmpresa
from catalogo.models import Familia, Producto
from usuarios.permissions import IsAdministrativeUser

from .serializers import (
    ExportarVentasParametrosSerializer,
    ResumenVentasParametrosSerializer,
)
from .services import (
    ReporteVentasService,
    exportar_pdf,
    exportar_xlsx,
)


class ReporteAdministrativoAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdministrativeUser]

    def obtener_empresa(self, request, empresa_slug):
        empresa = obtener_empresa_administrable(request)
        if empresa.slug.lower() != empresa_slug.lower():
            raise PermissionDenied("No puedes consultar reportes de otra empresa.")
        return empresa

    def validar_filtros(self, empresa, datos):
        errores = {}
        sucursal_id = datos.get("sucursal_id")
        examen_id = datos.get("examen_id")
        familia_id = datos.get("familia_id")

        if sucursal_id and not SucursalEmpresa.objects.filter(
            pk=sucursal_id,
            empresa=empresa,
        ).exists():
            errores["sucursal_id"] = "La sucursal no pertenece a la empresa."

        examen = None
        if examen_id:
            examen = Producto.objects.filter(
                pk=examen_id,
                empresa=empresa,
            ).first()
            if not examen:
                errores["examen_id"] = "El examen no pertenece a la empresa."

        if familia_id and not Familia.objects.filter(
            pk=familia_id,
            empresa=empresa,
        ).exists():
            errores["familia_id"] = "La familia no pertenece a la empresa."

        if examen and familia_id and examen.familia_id != familia_id:
            errores["examen_id"] = "El examen no pertenece a la familia seleccionada."

        if errores:
            raise ValidationError(errores)

    def filtros_servicio(self, datos):
        return {
            clave: datos.get(clave)
            for clave in ("ciudad", "sucursal_id", "examen_id", "familia_id")
            if datos.get(clave) not in (None, "")
        }


class ResumenVentasView(ReporteAdministrativoAPIView):
    def get(self, request):
        entrada = ResumenVentasParametrosSerializer(data=request.query_params)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data
        empresa = self.obtener_empresa(request, datos["empresa_slug"])
        self.validar_filtros(empresa, datos)
        servicio = ReporteVentasService(
            empresa=empresa,
            fecha_desde=datos["fecha_desde"],
            fecha_hasta=datos["fecha_hasta"],
            agrupacion=datos["agrupacion"],
            **self.filtros_servicio(datos),
        )
        return Response(
            servicio.construir_resumen(
                comparar_periodo_anterior=datos["comparar_periodo_anterior"]
            )
        )


class ExportarVentasView(ReporteAdministrativoAPIView):
    EXPORTADORES = {
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
        self.validar_filtros(empresa, datos)
        servicio = ReporteVentasService(
            empresa=empresa,
            fecha_desde=datos["fecha_desde"],
            fecha_hasta=datos["fecha_hasta"],
            **self.filtros_servicio(datos),
        )
        tabla = servicio.construir_tabla(datos["tipo"])
        exportador, content_type = self.EXPORTADORES[datos["formato"]]
        contenido = exportador(tabla)
        nombre = (
            f"reporte_{datos['tipo']}_"
            f"{datos['fecha_desde'].isoformat()}_{datos['fecha_hasta'].isoformat()}."
            f"{datos['formato']}"
        )
        respuesta = HttpResponse(contenido, content_type=content_type)
        respuesta["Content-Disposition"] = f'attachment; filename="{nombre}"'
        return respuesta
