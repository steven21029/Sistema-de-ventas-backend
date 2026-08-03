from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models.deletion import ProtectedError
from django.utils.dateparse import parse_date
from rest_framework.exceptions import ValidationError
from rest_framework import status
from rest_framework.response import Response

from .pagination import PaginacionAdministrativa


VALORES_VERDADEROS = {"true", "1", "si", "yes"}


class PaginacionAdministrativaOpcionalMixin:
    pagination_class = PaginacionAdministrativa

    def paginate_queryset(self, queryset):
        paginar = self.request.query_params.get("paginar", "").strip().lower()
        if paginar not in VALORES_VERDADEROS:
            return None
        return super().paginate_queryset(queryset)


class FiltroRangoFechasMixin:
    def filtrar_rango_fechas(self, queryset, campo="fecha_creacion"):
        for parametro, lookup in [
            ("fecha_desde", "gte"),
            ("fecha_hasta", "lte"),
        ]:
            valor = self.request.query_params.get(parametro, "").strip()
            if not valor:
                continue
            fecha = parse_date(valor)
            if not fecha:
                raise ValidationError(
                    {parametro: "Usa una fecha valida con formato AAAA-MM-DD."}
                )
            queryset = queryset.filter(**{f"{campo}__date__{lookup}": fecha})
        return queryset


class EliminacionProtegidaMixin:
    mensaje_eliminacion_protegida = (
        "Este registro tiene historial relacionado. Desactivalo en lugar de eliminarlo."
    )

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except (ProtectedError, DjangoValidationError) as exc:
            detalle = self.mensaje_eliminacion_protegida
            if isinstance(exc, DjangoValidationError):
                if hasattr(exc, "message_dict"):
                    detalle = exc.message_dict
                elif exc.messages:
                    detalle = exc.messages[0]
            return Response(
                {"detalle": detalle},
                status=status.HTTP_409_CONFLICT,
            )
