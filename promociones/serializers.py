from rest_framework import serializers

from catalogo.models import Producto

from .models import (
    BannerPromocional,
    DescuentoPromocional,
    OfertaPromocional,
)


class EmpresaContextoEntradaMixin:
    def to_internal_value(self, data):
        empresa = self.context.get("empresa")
        if empresa:
            data = data.copy()
            data["empresa"] = empresa.pk
        return super().to_internal_value(data)


class BannerPromocionalSerializer(
    EmpresaContextoEntradaMixin,
    serializers.ModelSerializer,
):
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    empresa_slug = serializers.CharField(source="empresa.slug", read_only=True)
    imagen_final = serializers.SerializerMethodField()
    esta_vigente = serializers.BooleanField(read_only=True)

    class Meta:
        model = BannerPromocional
        fields = [
            "id",
            "empresa",
            "empresa_nombre",
            "empresa_slug",
            "titulo",
            "subtitulo",
            "texto_boton",
            "url_boton",
            "imagen",
            "imagen_url",
            "imagen_final",
            "texto_alternativo",
            "orden",
            "activo",
            "esta_vigente",
            "fecha_inicio",
            "fecha_fin",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id",
            "empresa_nombre",
            "empresa_slug",
            "imagen_final",
            "esta_vigente",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        extra_kwargs = {"empresa": {"required": False}}

    def get_imagen_final(self, obj):
        if obj.imagen_url:
            return obj.imagen_url

        if not obj.imagen:
            return None

        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.imagen.url)

        return obj.imagen.url

    def validate(self, attrs):
        request = self.context.get("request")
        empresa_contexto = self.context.get("empresa")
        if empresa_contexto:
            attrs["empresa"] = empresa_contexto
        empresa = attrs.get("empresa") or getattr(self.instance, "empresa", None)
        imagen = attrs.get("imagen") or getattr(self.instance, "imagen", None)
        imagen_url = attrs.get("imagen_url") or getattr(self.instance, "imagen_url", "")
        fecha_inicio = attrs.get("fecha_inicio") or getattr(
            self.instance,
            "fecha_inicio",
            None,
        )
        fecha_fin = attrs.get("fecha_fin") or getattr(self.instance, "fecha_fin", None)

        if request and not request.user.is_superuser:
            perfil = getattr(request.user, "perfil", None)
            if perfil and not perfil.es_administrador_maestro:
                empresa_enviada = attrs.get("empresa")
                if empresa_enviada and empresa_enviada != perfil.empresa:
                    raise serializers.ValidationError(
                        {"empresa": "Solo puedes administrar banners de tu empresa."}
                    )
                empresa = perfil.empresa

        if not empresa:
            raise serializers.ValidationError(
                {"empresa": "Debes seleccionar la empresa del banner."}
            )

        if not imagen and not imagen_url:
            raise serializers.ValidationError(
                {"imagen": "Debes agregar una imagen local o una URL externa."}
            )

        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            raise serializers.ValidationError(
                {"fecha_fin": "La fecha final no puede ser menor que la fecha inicial."}
            )

        return attrs


class BannerPromocionalPublicoSerializer(BannerPromocionalSerializer):
    class Meta:
        model = BannerPromocional
        fields = [
            "titulo",
            "subtitulo",
            "texto_boton",
            "url_boton",
            "imagen_final",
            "texto_alternativo",
            "orden",
        ]
        read_only_fields = fields


class ProductoOfertaPublicoSerializer(serializers.Serializer):
    codigo = serializers.CharField(source="codigo_venta")
    codigo_barra = serializers.CharField(allow_null=True)
    tipo_item = serializers.CharField()
    controla_inventario = serializers.BooleanField()
    nombre = serializers.CharField()
    precio = serializers.DecimalField(max_digits=12, decimal_places=2)


class OfertaPromocionalSerializer(
    EmpresaContextoEntradaMixin,
    serializers.ModelSerializer,
):
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    empresa_slug = serializers.CharField(source="empresa.slug", read_only=True)
    tipo_nombre = serializers.CharField(source="get_tipo_display", read_only=True)
    imagen_final = serializers.SerializerMethodField()
    esta_vigente = serializers.BooleanField(read_only=True)
    productos = serializers.SerializerMethodField()
    productos_ids = serializers.PrimaryKeyRelatedField(
        source="productos",
        queryset=Producto.objects.all(),
        many=True,
        write_only=True,
        required=False,
    )
    paquete_resumen = serializers.SerializerMethodField()

    class Meta:
        model = OfertaPromocional
        fields = [
            "id",
            "empresa",
            "empresa_nombre",
            "empresa_slug",
            "tipo",
            "tipo_nombre",
            "codigo",
            "titulo",
            "descripcion",
            "precio_normal",
            "precio_oferta",
            "porcentaje_descuento",
            "imagen",
            "imagen_url",
            "imagen_final",
            "url_destino",
            "paquete",
            "paquete_resumen",
            "productos",
            "productos_ids",
            "orden",
            "activo",
            "esta_vigente",
            "fecha_inicio",
            "fecha_fin",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id",
            "empresa_nombre",
            "empresa_slug",
            "tipo_nombre",
            "imagen_final",
            "esta_vigente",
            "paquete_resumen",
            "productos",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        extra_kwargs = {"empresa": {"required": False}}

    def get_imagen_final(self, obj):
        if obj.imagen_url:
            return obj.imagen_url

        if not obj.imagen:
            return None

        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.imagen.url)

        return obj.imagen.url

    def get_productos(self, obj):
        items = obj.items_productos.select_related("producto").filter(
            producto__activo=True
        )
        return [
            {
                "codigo": item.producto.codigo_venta,
                "codigo_barra": item.producto.codigo_barra,
                "tipo_item": item.producto.tipo_item,
                "controla_inventario": item.producto.controla_inventario,
                "nombre": item.producto.nombre,
                "precio": item.producto.precio,
            }
            for item in items
        ]

    def get_paquete_resumen(self, obj):
        if not obj.paquete_id:
            return None

        return {
            "codigo": obj.paquete.codigo,
            "nombre": obj.paquete.nombre,
            "tipo": obj.paquete.tipo,
        }

    def validate(self, attrs):
        request = self.context.get("request")
        empresa_contexto = self.context.get("empresa")
        if empresa_contexto:
            attrs["empresa"] = empresa_contexto
        empresa = attrs.get("empresa") or getattr(self.instance, "empresa", None)
        paquete = attrs.get("paquete") or getattr(self.instance, "paquete", None)

        if request and not request.user.is_superuser:
            perfil = getattr(request.user, "perfil", None)
            if perfil and not perfil.es_administrador_maestro:
                empresa_enviada = attrs.get("empresa")
                if empresa_enviada and empresa_enviada != perfil.empresa:
                    raise serializers.ValidationError(
                        {"empresa": "Solo puedes administrar ofertas de tu empresa."}
                    )
                empresa = perfil.empresa

        if not empresa:
            raise serializers.ValidationError(
                {"empresa": "Debes seleccionar la empresa de la oferta."}
            )

        if paquete and paquete.empresa != empresa:
            raise serializers.ValidationError(
                {"paquete": "El paquete debe pertenecer a la misma empresa."}
            )

        productos = attrs.get("productos")
        if productos is None and self.instance:
            productos = list(self.instance.productos.all())
        productos = productos or []
        if len(productos) != len({producto.pk for producto in productos}):
            raise serializers.ValidationError(
                {"productos_ids": "No puedes repetir productos en la oferta."}
            )
        if empresa and any(
            producto.empresa_id != empresa.id for producto in productos
        ):
            raise serializers.ValidationError(
                {"productos_ids": "Todos los productos deben pertenecer a la empresa."}
            )

        tipo = attrs.get("tipo", getattr(self.instance, "tipo", None))
        if tipo == OfertaPromocional.Tipo.PRODUCTO and len(productos) != 1:
            raise serializers.ValidationError(
                {"productos_ids": "La oferta de producto requiere exactamente uno."}
            )
        if tipo == OfertaPromocional.Tipo.PRODUCTOS and len(productos) < 2:
            raise serializers.ValidationError(
                {"productos_ids": "La oferta de varios productos requiere al menos dos."}
            )
        if tipo == OfertaPromocional.Tipo.PAQUETE and productos:
            raise serializers.ValidationError(
                {"productos_ids": "La oferta de paquete no debe seleccionar productos."}
            )

        precio_normal = attrs.get(
            "precio_normal",
            getattr(self.instance, "precio_normal", None),
        )
        precio_oferta = attrs.get(
            "precio_oferta",
            getattr(self.instance, "precio_oferta", None),
        )
        if (
            precio_normal is not None
            and precio_oferta is not None
            and precio_oferta > precio_normal
        ):
            raise serializers.ValidationError(
                {"precio_oferta": "El precio de oferta no puede superar el precio normal."}
            )

        return attrs

    def create(self, validated_data):
        productos = validated_data.pop("productos", [])
        instance = super().create(validated_data)
        instance.productos.set(productos)
        return instance

    def update(self, instance, validated_data):
        productos = validated_data.pop("productos", None)
        instance = super().update(instance, validated_data)
        if productos is not None:
            instance.productos.set(productos)
        return instance


class OfertaPromocionalPublicaSerializer(OfertaPromocionalSerializer):
    class Meta:
        model = OfertaPromocional
        fields = [
            "tipo",
            "codigo",
            "titulo",
            "descripcion",
            "precio_normal",
            "precio_oferta",
            "porcentaje_descuento",
            "imagen_final",
            "url_destino",
            "paquete_resumen",
            "productos",
            "orden",
            "fecha_inicio",
            "fecha_fin",
        ]
        read_only_fields = fields


class DescuentoPromocionalSerializer(
    EmpresaContextoEntradaMixin,
    serializers.ModelSerializer,
):
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    empresa_slug = serializers.CharField(source="empresa.slug", read_only=True)
    alcance_nombre = serializers.CharField(
        source="get_alcance_display",
        read_only=True,
    )
    esta_vigente = serializers.BooleanField(read_only=True)
    productos_ids = serializers.PrimaryKeyRelatedField(
        source="productos",
        queryset=Producto.objects.all(),
        many=True,
        write_only=True,
        required=False,
    )
    productos = serializers.SerializerMethodField()

    class Meta:
        model = DescuentoPromocional
        fields = [
            "id",
            "empresa",
            "empresa_nombre",
            "empresa_slug",
            "codigo",
            "titulo",
            "descripcion",
            "alcance",
            "alcance_nombre",
            "porcentaje",
            "productos_ids",
            "productos",
            "activo",
            "esta_vigente",
            "fecha_inicio",
            "fecha_fin",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id",
            "empresa_nombre",
            "empresa_slug",
            "alcance_nombre",
            "productos",
            "esta_vigente",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        extra_kwargs = {"empresa": {"required": False}}

    def get_productos(self, obj):
        return [
            {
                "id": producto.id,
                "codigo": producto.codigo_venta,
                "codigo_barra": producto.codigo_barra,
                "tipo_item": producto.tipo_item,
                "controla_inventario": producto.controla_inventario,
                "nombre": producto.nombre,
                "precio": producto.precio,
            }
            for producto in obj.productos.all()
        ]

    def validate(self, attrs):
        request = self.context.get("request")
        empresa_contexto = self.context.get("empresa")
        if empresa_contexto:
            attrs["empresa"] = empresa_contexto
        empresa = attrs.get("empresa") or getattr(self.instance, "empresa", None)

        if request and not request.user.is_superuser:
            perfil = getattr(request.user, "perfil", None)
            if perfil and not perfil.es_administrador_maestro:
                empresa_enviada = attrs.get("empresa")
                if empresa_enviada and empresa_enviada != perfil.empresa:
                    raise serializers.ValidationError(
                        {"empresa": "Solo puedes administrar descuentos de tu empresa."}
                    )
                empresa = perfil.empresa

        if not empresa:
            raise serializers.ValidationError(
                {"empresa": "Debes seleccionar la empresa del descuento."}
            )

        fecha_inicio = attrs.get(
            "fecha_inicio",
            getattr(self.instance, "fecha_inicio", None),
        )
        fecha_fin = attrs.get(
            "fecha_fin",
            getattr(self.instance, "fecha_fin", None),
        )
        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            raise serializers.ValidationError(
                {"fecha_fin": "La fecha final no puede ser menor que la fecha inicial."}
            )

        alcance = attrs.get(
            "alcance",
            getattr(self.instance, "alcance", None),
        )
        if "productos" in attrs:
            productos = attrs["productos"]
        elif self.instance:
            productos = list(self.instance.productos.all())
        else:
            productos = []

        productos_repetidos = len(productos) != len(
            {producto.pk for producto in productos}
        )
        if productos_repetidos:
            raise serializers.ValidationError(
                {"productos_ids": "No puedes repetir un articulo en el descuento."}
            )

        if any(producto.empresa_id != empresa.id for producto in productos):
            raise serializers.ValidationError(
                {
                    "productos_ids": (
                        "Todos los articulos deben pertenecer a la misma empresa "
                        "del descuento."
                    )
                }
            )

        cantidad = len(productos)
        if alcance == DescuentoPromocional.Alcance.TODOS and cantidad:
            raise serializers.ValidationError(
                {
                    "productos_ids": (
                        "El alcance para todos los articulos no debe seleccionar "
                        "productos."
                    )
                }
            )
        if alcance == DescuentoPromocional.Alcance.INDIVIDUAL and cantidad != 1:
            raise serializers.ValidationError(
                {
                    "productos_ids": (
                        "El alcance individual debe seleccionar exactamente "
                        "un articulo."
                    )
                }
            )
        if (
            alcance == DescuentoPromocional.Alcance.SELECCIONADOS
            and cantidad < 2
        ):
            raise serializers.ValidationError(
                {
                    "productos_ids": (
                        "El alcance de articulos seleccionados requiere al menos dos."
                    )
                }
            )

        return attrs

    def create(self, validated_data):
        productos = validated_data.pop("productos", [])
        instance = super().create(validated_data)
        instance.productos.set(productos)
        return instance

    def update(self, instance, validated_data):
        productos = validated_data.pop("productos", None)
        instance = super().update(instance, validated_data)
        if productos is not None:
            instance.productos.set(productos)
        return instance


class DescuentoPromocionalPublicoSerializer(DescuentoPromocionalSerializer):
    class Meta:
        model = DescuentoPromocional
        fields = [
            "codigo",
            "titulo",
            "descripcion",
            "alcance",
            "alcance_nombre",
            "porcentaje",
            "productos",
            "fecha_inicio",
            "fecha_fin",
        ]
        read_only_fields = fields
