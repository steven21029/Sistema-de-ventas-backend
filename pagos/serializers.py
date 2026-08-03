from rest_framework import serializers

from .models import Pago


class PagoSerializer(serializers.ModelSerializer):
    pedido_numero = serializers.CharField(source="pedido.numero", read_only=True)
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    empresa_slug = serializers.CharField(source="empresa.slug", read_only=True)
    usuario_email = serializers.EmailField(source="usuario.email", read_only=True)
    estado_nombre = serializers.CharField(source="get_estado_display", read_only=True)

    class Meta:
        model = Pago
        fields = [
            "id",
            "referencia",
            "pedido",
            "pedido_numero",
            "empresa",
            "empresa_nombre",
            "empresa_slug",
            "usuario",
            "usuario_email",
            "proveedor",
            "identificador_externo",
            "monto",
            "moneda",
            "estado",
            "estado_nombre",
            "url_pago",
            "codigo_respuesta",
            "fecha_confirmacion",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = fields


class IniciarPagoSerializer(serializers.Serializer):
    pedido_id = serializers.IntegerField(min_value=1)


class WebhookPagoSerializer(serializers.Serializer):
    evento_id = serializers.CharField(max_length=150)
    referencia = serializers.UUIDField()
    estado = serializers.ChoiceField(
        choices=[Pago.Estado.APROBADO, Pago.Estado.RECHAZADO]
    )
    identificador_externo = serializers.CharField(max_length=150)
    codigo_respuesta = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        default="",
    )

    def validate_evento_id(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("El evento no puede estar vacio.")
        return value

    def validate_identificador_externo(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError(
                "El identificador externo no puede estar vacio."
            )
        return value
