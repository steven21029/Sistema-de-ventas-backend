from django.utils.text import slugify
from rest_framework import serializers

from .models import Categoria, Familia, PaqueteCatalogo, Producto


class ImagenFinalMixin:
    imagen_final = serializers.SerializerMethodField()

    def get_imagen_final(self, obj):
        imagen_url = getattr(obj, "imagen_url", "")
        if imagen_url:
            return imagen_url

        imagen = getattr(obj, "imagen_principal", None) or getattr(obj, "imagen", None)
        if not imagen:
            return None

        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(imagen.url)

        return imagen.url


class FamiliaSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    imagen_final = serializers.SerializerMethodField()

    class Meta:
        model = Familia
        fields = [
            "id",
            "empresa",
            "empresa_nombre",
            "nombre",
            "descripcion",
            "imagen",
            "imagen_url",
            "imagen_final",
            "activa",
            "orden",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id",
            "empresa_nombre",
            "imagen_final",
            "orden",
            "fecha_creacion",
            "fecha_actualizacion",
        ]

    def get_imagen_final(self, obj):
        if obj.imagen_url:
            return obj.imagen_url

        if not obj.imagen:
            return None

        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.imagen.url)

        return obj.imagen.url


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
    inventario_bajo = serializers.BooleanField(read_only=True)
    estado_inventario = serializers.CharField(read_only=True)
    imagen_final = serializers.SerializerMethodField()

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
            "imagen_url",
            "imagen_final",
            "precio",
            "existencia",
            "existencia_minima",
            "orden_destacado",
            "agotado",
            "inventario_bajo",
            "estado_inventario",
            "activo",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "empresa_nombre",
            "familia_nombre",
            "categoria_nombre",
            "imagen_final",
            "existencia",
            "agotado",
            "inventario_bajo",
            "estado_inventario",
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

    def get_imagen_final(self, obj):
        if obj.imagen_url:
            return obj.imagen_url

        if not obj.imagen_principal:
            return None

        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.imagen_principal.url)

        return obj.imagen_principal.url


class ProductoPaginaPublicaSerializer(ImagenFinalMixin, serializers.ModelSerializer):
    familia_nombre = serializers.CharField(source="familia.nombre", read_only=True)
    categoria_nombre = serializers.CharField(source="categoria.nombre", read_only=True)
    agotado = serializers.BooleanField(read_only=True)

    class Meta:
        model = Producto
        fields = [
            "codigo_barra",
            "nombre",
            "descripcion",
            "precio",
            "imagen_final",
            "categoria_nombre",
            "familia_nombre",
            "agotado",
            "existencia",
        ]
        read_only_fields = fields


class ProductoPaquetePublicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = [
            "codigo_barra",
            "nombre",
            "precio",
        ]
        read_only_fields = fields


class ComboDestacadoPublicoSerializer(ImagenFinalMixin, serializers.ModelSerializer):
    precio_combo = serializers.DecimalField(
        source="precio_paquete",
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )
    productos = serializers.SerializerMethodField()

    class Meta:
        model = PaqueteCatalogo
        fields = [
            "codigo",
            "nombre",
            "descripcion",
            "precio_normal",
            "precio_combo",
            "porcentaje_descuento",
            "imagen_final",
            "productos",
            "orden",
        ]
        read_only_fields = fields

    def get_productos(self, obj):
        items = obj.items_productos.select_related("producto").filter(
            producto__activo=True
        )
        return [
            {
                "codigo_barra": item.producto.codigo_barra,
                "nombre": item.producto.nombre,
            }
            for item in items
        ]


class PerfilPublicoSerializer(ImagenFinalMixin, serializers.ModelSerializer):
    precio_perfil = serializers.DecimalField(
        source="precio_paquete",
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )
    productos = serializers.SerializerMethodField()
    agotado = serializers.BooleanField(read_only=True)

    class Meta:
        model = PaqueteCatalogo
        fields = [
            "codigo",
            "nombre",
            "descripcion",
            "precio_normal",
            "precio_perfil",
            "porcentaje_descuento",
            "imagen_final",
            "productos",
            "agotado",
            "orden",
        ]
        read_only_fields = fields

    def get_productos(self, obj):
        productos = [
            item.producto
            for item in obj.items_productos.select_related("producto").filter(
                producto__activo=True
            )
        ]
        return ProductoPaquetePublicoSerializer(productos, many=True).data


class CategoriaServicioPublicoSerializer(serializers.ModelSerializer):
    clave = serializers.SerializerMethodField()
    cantidad_productos = serializers.IntegerField(read_only=True)

    class Meta:
        model = Categoria
        fields = [
            "clave",
            "nombre",
            "descripcion",
            "orden",
            "cantidad_productos",
        ]
        read_only_fields = fields

    def get_clave(self, obj):
        return slugify(obj.nombre)


class CategoriaServicioDetalleSerializer(CategoriaServicioPublicoSerializer):
    productos = serializers.SerializerMethodField()

    class Meta(CategoriaServicioPublicoSerializer.Meta):
        fields = CategoriaServicioPublicoSerializer.Meta.fields + ["productos"]
        read_only_fields = fields

    def get_productos(self, obj):
        productos = getattr(obj, "productos_activos", None)
        if productos is None:
            productos = obj.productos.filter(
                activo=True,
                familia__activa=True,
                categoria__activa=True,
            ).order_by("nombre")

        return ProductoPaginaPublicaSerializer(
            productos,
            many=True,
            context=self.context,
        ).data


class ServicioPublicoSerializer(ImagenFinalMixin, serializers.ModelSerializer):
    clave = serializers.SerializerMethodField()
    cantidad_productos = serializers.IntegerField(read_only=True)
    cantidad_categorias = serializers.IntegerField(read_only=True)
    categorias = serializers.SerializerMethodField()

    class Meta:
        model = Familia
        fields = [
            "clave",
            "nombre",
            "descripcion",
            "imagen_final",
            "orden",
            "cantidad_categorias",
            "cantidad_productos",
            "categorias",
        ]
        read_only_fields = fields

    def get_clave(self, obj):
        return slugify(obj.nombre)

    def get_categorias(self, obj):
        categorias = getattr(obj, "categorias_activas", None)
        if categorias is None:
            categorias = obj.categorias.filter(activa=True).order_by("orden", "nombre")

        return CategoriaServicioPublicoSerializer(
            categorias,
            many=True,
            context=self.context,
        ).data


class ServicioDetallePublicoSerializer(ServicioPublicoSerializer):
    categorias = serializers.SerializerMethodField()

    def get_categorias(self, obj):
        categorias = getattr(obj, "categorias_activas", None)
        if categorias is None:
            categorias = obj.categorias.filter(activa=True).order_by("orden", "nombre")

        return CategoriaServicioDetalleSerializer(
            categorias,
            many=True,
            context=self.context,
        ).data
