from rest_framework import serializers


class ParametrosPeriodoSerializer(serializers.Serializer):
    empresa_slug = serializers.SlugField(max_length=170)
    fecha_desde = serializers.DateField(input_formats=["%Y-%m-%d"])
    fecha_hasta = serializers.DateField(input_formats=["%Y-%m-%d"])

    def validate(self, attrs):
        if attrs["fecha_desde"] > attrs["fecha_hasta"]:
            raise serializers.ValidationError(
                {"fecha_hasta": "Debe ser igual o posterior a fecha_desde."}
            )
        return attrs


class ResumenVentasParametrosSerializer(ParametrosPeriodoSerializer):
    agrupacion = serializers.ChoiceField(
        choices=["dia", "mes"],
        default="dia",
    )
    comparar_periodo_anterior = serializers.BooleanField(default=False)


class ExportarVentasParametrosSerializer(ParametrosPeriodoSerializer):
    formato = serializers.ChoiceField(choices=["csv", "xlsx", "pdf"])
    tipo = serializers.ChoiceField(
        choices=["resumen", "ventas", "pagos", "impuestos"]
    )
