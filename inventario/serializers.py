from rest_framework import serializers

from catalogo.models import Producto
from .models import MovimientoInventario


class ProductoInventarioSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    empresa_slug = serializers.CharField(source="empresa.slug", read_only=True)
    familia_nombre = serializers.CharField(source="familia.nombre", read_only=True)
    categoria_nombre = serializers.CharField(source="categoria.nombre", read_only=True)
    agotado = serializers.BooleanField(read_only=True)
    inventario_bajo = serializers.BooleanField(read_only=True)
    estado_inventario = serializers.CharField(read_only=True)
    codigo = serializers.CharField(source="codigo_venta", read_only=True)
    tipo_item_nombre = serializers.CharField(
        source="get_tipo_item_display",
        read_only=True,
    )
    controla_inventario = serializers.BooleanField(read_only=True)

    class Meta:
        model = Producto
        fields = [
            "empresa_nombre",
            "empresa_slug",
            "familia_nombre",
            "categoria_nombre",
            "codigo",
            "codigo_interno",
            "codigo_barra",
            "tipo_item",
            "tipo_item_nombre",
            "nombre",
            "precio",
            "existencia",
            "existencia_minima",
            "agotado",
            "inventario_bajo",
            "estado_inventario",
            "controla_inventario",
            "activo",
            "fecha_actualizacion",
        ]


class AjustarExistenciaSerializer(serializers.Serializer):
    empresa_slug = serializers.CharField(required=False, allow_blank=True)
    codigo_barra = serializers.CharField()
    existencia_nueva = serializers.IntegerField(min_value=0)
    motivo = serializers.CharField(required=False, allow_blank=True)
    referencia = serializers.CharField(required=False, allow_blank=True, max_length=120)


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

        if producto and not producto.controla_inventario:
            raise serializers.ValidationError(
                {"producto": "Los servicios no admiten movimientos de inventario."}
            )

        if attrs.get("tipo") in [
            MovimientoInventario.Tipo.ENTRADA,
            MovimientoInventario.Tipo.SALIDA,
        ] and attrs.get("cantidad", 0) < 1:
            raise serializers.ValidationError(
                {"cantidad": "Las entradas y salidas deben ser mayores que cero."}
            )

        if attrs.get("tipo") == MovimientoInventario.Tipo.SALIDA and producto:
            if attrs.get("cantidad", 0) > producto.existencia:
                raise serializers.ValidationError(
                    {"cantidad": "No se puede registrar una salida mayor a la existencia actual."}
                )

        return attrs
