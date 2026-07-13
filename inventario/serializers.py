from rest_framework import serializers

from .models import MovimientoInventario


class MovimientoInventarioSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)
    codigo_barra = serializers.CharField(source="producto.codigo_barra", read_only=True)
    tipo_nombre = serializers.CharField(source="get_tipo_display", read_only=True)
    usuario_nombre = serializers.CharField(source="usuario.username", read_only=True)

    class Meta:
        model = MovimientoInventario
        fields = [
            "id",
            "empresa",
            "empresa_nombre",
            "producto",
            "producto_nombre",
            "codigo_barra",
            "tipo",
            "tipo_nombre",
            "cantidad",
            "existencia_anterior",
            "existencia_nueva",
            "motivo",
            "referencia",
            "usuario",
            "usuario_nombre",
            "fecha_creacion",
        ]
        read_only_fields = [
            "id",
            "empresa_nombre",
            "producto_nombre",
            "codigo_barra",
            "tipo_nombre",
            "existencia_anterior",
            "existencia_nueva",
            "usuario",
            "usuario_nombre",
            "fecha_creacion",
        ]

    def validate(self, attrs):
        request = self.context.get("request")
        empresa = attrs.get("empresa")
        producto = attrs.get("producto")

        if request and not request.user.is_superuser:
            perfil = getattr(request.user, "perfil", None)
            empresa = perfil.empresa if perfil else empresa

        if empresa and producto and empresa != producto.empresa:
            raise serializers.ValidationError(
                {"producto": "El producto debe pertenecer a la misma empresa del movimiento."}
            )

        if attrs.get("tipo") == MovimientoInventario.Tipo.SALIDA and producto:
            if attrs.get("cantidad", 0) > producto.existencia:
                raise serializers.ValidationError(
                    {"cantidad": "No se puede registrar una salida mayor a la existencia actual."}
                )

        return attrs
