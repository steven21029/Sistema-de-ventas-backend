from rest_framework import serializers

from catalogo.models import Producto
from empresas.models import Empresa
from .models import Favorito


class FavoritoSerializer(serializers.ModelSerializer):
    empresa_slug = serializers.CharField(write_only=True, required=False)
    codigo_barra = serializers.CharField(write_only=True)
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)
    producto_codigo_barra = serializers.CharField(
        source="producto.codigo_barra",
        read_only=True,
    )
    producto_imagen_principal = serializers.ImageField(
        source="producto.imagen_principal",
        read_only=True,
    )
    producto_precio = serializers.DecimalField(
        source="producto.precio",
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )
    producto_agotado = serializers.BooleanField(source="producto.agotado", read_only=True)

    class Meta:
        model = Favorito
        fields = [
            "id",
            "empresa_slug",
            "codigo_barra",
            "empresa_nombre",
            "producto_nombre",
            "producto_codigo_barra",
            "producto_imagen_principal",
            "producto_precio",
            "producto_agotado",
            "fecha_creacion",
        ]
        read_only_fields = [
            "id",
            "empresa_nombre",
            "producto_nombre",
            "producto_codigo_barra",
            "producto_imagen_principal",
            "producto_precio",
            "producto_agotado",
            "fecha_creacion",
        ]

    def validate(self, attrs):
        request = self.context["request"]
        empresa_slug = attrs.get("empresa_slug", "").strip()

        if request.user.is_superuser:
            if not empresa_slug:
                raise serializers.ValidationError(
                    {"empresa_slug": "Debes enviar el slug de la empresa."}
                )
            empresa = self._obtener_empresa(empresa_slug)
        else:
            perfil = getattr(request.user, "perfil", None)
            if not perfil or not perfil.activo or not perfil.empresa_id:
                raise serializers.ValidationError(
                    {"empresa_slug": "El usuario no tiene una empresa activa."}
                )

            empresa = perfil.empresa
            if empresa_slug and empresa.slug.lower() != empresa_slug.lower():
                raise serializers.ValidationError(
                    {"empresa_slug": "No puedes guardar favoritos de otra empresa."}
                )

        producto = Producto.objects.filter(
            empresa=empresa,
            codigo_barra=attrs["codigo_barra"].strip(),
            activo=True,
            familia__activa=True,
            categoria__activa=True,
        ).first()
        if not producto:
            raise serializers.ValidationError(
                {"codigo_barra": "El producto no existe o no esta activo."}
            )

        attrs["empresa"] = empresa
        attrs["producto"] = producto
        attrs["usuario"] = request.user
        return attrs

    def _obtener_empresa(self, slug):
        empresa = Empresa.objects.filter(slug__iexact=slug, activa=True).first()
        if not empresa:
            raise serializers.ValidationError(
                {"empresa_slug": "La empresa no existe o no esta activa."}
            )

        return empresa

    def create(self, validated_data):
        validated_data.pop("empresa_slug", None)
        validated_data.pop("codigo_barra", None)
        favorito, _created = Favorito.objects.get_or_create(**validated_data)
        return favorito
