from django.db.models import Q
from rest_framework import serializers

from catalogo.models import PaqueteCatalogo, Producto
from empresas.models import Empresa
from .models import Favorito


class FavoritoSerializer(serializers.ModelSerializer):
    TIPOS_ARTICULO = [
        ("producto", "Producto o servicio"),
        (PaqueteCatalogo.Tipo.PERFIL, "Perfil"),
        (PaqueteCatalogo.Tipo.COMBO, "Combo"),
    ]

    empresa_slug = serializers.CharField(write_only=True, required=False)
    codigo = serializers.CharField(write_only=True, required=False)
    codigo_barra = serializers.CharField(write_only=True, required=False)
    tipo_articulo = serializers.ChoiceField(
        choices=TIPOS_ARTICULO,
        required=False,
    )
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    articulo_codigo = serializers.SerializerMethodField()
    articulo_nombre = serializers.SerializerMethodField()
    articulo_descripcion = serializers.SerializerMethodField()
    articulo_imagen_final = serializers.SerializerMethodField()
    articulo_precio = serializers.SerializerMethodField()
    articulo_agotado = serializers.SerializerMethodField()
    articulo_familia = serializers.SerializerMethodField()
    articulo_categoria = serializers.SerializerMethodField()
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)
    producto_codigo = serializers.CharField(
        source="producto.codigo_venta",
        read_only=True,
    )
    producto_codigo_barra = serializers.CharField(
        source="producto.codigo_barra",
        read_only=True,
    )
    producto_imagen_principal = serializers.SerializerMethodField()
    producto_precio = serializers.DecimalField(
        source="producto.precio",
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )
    producto_agotado = serializers.BooleanField(source="producto.agotado", read_only=True)
    producto_tipo_item = serializers.CharField(
        source="producto.tipo_item",
        read_only=True,
    )
    producto_controla_inventario = serializers.BooleanField(
        source="producto.controla_inventario",
        read_only=True,
    )

    class Meta:
        model = Favorito
        fields = [
            "id",
            "empresa_slug",
            "codigo",
            "codigo_barra",
            "tipo_articulo",
            "empresa_nombre",
            "articulo_codigo",
            "articulo_nombre",
            "articulo_descripcion",
            "articulo_imagen_final",
            "articulo_precio",
            "articulo_agotado",
            "articulo_familia",
            "articulo_categoria",
            "producto_nombre",
            "producto_codigo",
            "producto_codigo_barra",
            "producto_imagen_principal",
            "producto_precio",
            "producto_agotado",
            "producto_tipo_item",
            "producto_controla_inventario",
            "fecha_creacion",
        ]
        read_only_fields = [
            "id",
            "empresa_nombre",
            "articulo_codigo",
            "articulo_nombre",
            "articulo_descripcion",
            "articulo_imagen_final",
            "articulo_precio",
            "articulo_agotado",
            "articulo_familia",
            "articulo_categoria",
            "producto_nombre",
            "producto_codigo",
            "producto_codigo_barra",
            "producto_imagen_principal",
            "producto_precio",
            "producto_agotado",
            "producto_tipo_item",
            "producto_controla_inventario",
            "fecha_creacion",
        ]

    def validate(self, attrs):
        request = self.context["request"]
        empresa_slug = attrs.get("empresa_slug", "").strip()
        codigo = (attrs.get("codigo") or attrs.get("codigo_barra") or "").strip()
        tipo_articulo = attrs.get("tipo_articulo")
        if not codigo:
            raise serializers.ValidationError(
                {"codigo": "Debes enviar el codigo del articulo."}
            )

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

        producto = None
        paquete = None
        if tipo_articulo in [None, "producto"]:
            producto = Producto.objects.filter(
                Q(codigo_interno__iexact=codigo)
                | Q(codigo_barra__iexact=codigo),
                empresa=empresa,
                activo=True,
                familia__activa=True,
                categoria__activa=True,
            ).first()

        if tipo_articulo in [
            None,
            PaqueteCatalogo.Tipo.PERFIL,
            PaqueteCatalogo.Tipo.COMBO,
        ]:
            paquetes = PaqueteCatalogo.objects.filter(
                empresa=empresa,
                codigo__iexact=codigo,
                activo=True,
            )
            if tipo_articulo:
                paquetes = paquetes.filter(tipo=tipo_articulo)
            paquete = paquetes.first()

        if tipo_articulo is None and producto and paquete:
            raise serializers.ValidationError(
                {
                    "tipo_articulo": (
                        "El codigo coincide con más de un tipo. "
                        "Debes indicar producto, perfil o combo."
                    )
                }
            )

        if not producto and not paquete:
            raise serializers.ValidationError(
                {"codigo": "El articulo no existe o no esta activo."}
            )

        attrs["empresa"] = empresa
        attrs["producto"] = producto
        attrs["paquete"] = paquete
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
        validated_data.pop("codigo", None)
        validated_data.pop("codigo_barra", None)
        validated_data.pop("tipo_articulo", None)
        favorito, _created = Favorito.objects.get_or_create(**validated_data)
        return favorito

    def get_articulo_codigo(self, obj):
        if obj.producto_id:
            return obj.producto.codigo_venta

        return obj.paquete.codigo

    def get_articulo_nombre(self, obj):
        return obj.articulo.nombre

    def get_articulo_descripcion(self, obj):
        return obj.articulo.descripcion

    def get_articulo_imagen_final(self, obj):
        return self._imagen_absoluta(obj.articulo.imagen_final)

    def get_articulo_precio(self, obj):
        precio = (
            obj.producto.precio
            if obj.producto_id
            else obj.paquete.precio_paquete
        )
        return f"{precio:.2f}"

    def get_articulo_agotado(self, obj):
        return obj.articulo.agotado

    def get_articulo_familia(self, obj):
        return obj.producto.familia.nombre if obj.producto_id else None

    def get_articulo_categoria(self, obj):
        return obj.producto.categoria.nombre if obj.producto_id else None

    def get_producto_imagen_principal(self, obj):
        if not obj.producto_id:
            return None

        return self._imagen_absoluta(obj.producto.imagen_final)

    def _imagen_absoluta(self, imagen):
        if not imagen:
            return None

        if imagen.startswith(("http://", "https://")):
            return imagen

        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(imagen)

        return imagen
