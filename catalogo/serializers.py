from rest_framework import serializers

from .models import Categoria, Familia, Producto


class FamiliaSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)

    class Meta:
        model = Familia
        fields = [
            "id",
            "empresa",
            "empresa_nombre",
            "nombre",
            "descripcion",
            "activa",
            "orden",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id",
            "empresa_nombre",
            "orden",
            "fecha_creacion",
            "fecha_actualizacion",
        ]


class CategoriaSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    familia_nombre = serializers.CharField(source="familia.nombre", read_only=True)

    class Meta:
        model = Categoria
        fields = [
            "id",
            "empresa",
            "empresa_nombre",
            "familia",
            "familia_nombre",
            "nombre",
            "descripcion",
            "activa",
            "orden",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id",
            "empresa_nombre",
            "familia_nombre",
            "orden",
            "fecha_creacion",
            "fecha_actualizacion",
        ]

    def validate(self, attrs):
        empresa = attrs.get("empresa") or getattr(self.instance, "empresa", None)
        familia = attrs.get("familia") or getattr(self.instance, "familia", None)

        if empresa and familia and empresa != familia.empresa:
            raise serializers.ValidationError(
                {"familia": "La categoria debe pertenecer a una familia de la misma empresa."}
            )

        return attrs


class ProductoSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    familia_nombre = serializers.CharField(source="familia.nombre", read_only=True)
    categoria_nombre = serializers.CharField(source="categoria.nombre", read_only=True)
    agotado = serializers.BooleanField(read_only=True)

    class Meta:
        model = Producto
        fields = [
            "empresa",
            "empresa_nombre",
            "familia",
            "familia_nombre",
            "categoria",
            "categoria_nombre",
            "codigo_barra",
            "nombre",
            "descripcion",
            "imagen_principal",
            "precio",
            "existencia",
            "agotado",
            "activo",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "empresa_nombre",
            "familia_nombre",
            "categoria_nombre",
            "agotado",
            "fecha_creacion",
            "fecha_actualizacion",
        ]

    def validate(self, attrs):
        empresa = attrs.get("empresa") or getattr(self.instance, "empresa", None)
        familia = attrs.get("familia") or getattr(self.instance, "familia", None)
        categoria = attrs.get("categoria") or getattr(self.instance, "categoria", None)

        if empresa and familia and empresa != familia.empresa:
            raise serializers.ValidationError(
                {"familia": "El producto debe pertenecer a una familia de la misma empresa."}
            )

        if empresa and categoria and empresa != categoria.empresa:
            raise serializers.ValidationError(
                {"categoria": "El producto debe pertenecer a una categoria de la misma empresa."}
            )

        if familia and categoria and categoria.familia != familia:
            raise serializers.ValidationError(
                {"categoria": "La categoria debe pertenecer a la familia seleccionada."}
            )

        return attrs
