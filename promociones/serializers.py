from rest_framework import serializers

from .models import BannerPromocional, OfertaPromocional


class BannerPromocionalSerializer(serializers.ModelSerializer):
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
    codigo_barra = serializers.CharField()
    nombre = serializers.CharField()
    precio = serializers.DecimalField(max_digits=12, decimal_places=2)


class OfertaPromocionalSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    empresa_slug = serializers.CharField(source="empresa.slug", read_only=True)
    tipo_nombre = serializers.CharField(source="get_tipo_display", read_only=True)
    imagen_final = serializers.SerializerMethodField()
    esta_vigente = serializers.BooleanField(read_only=True)
    productos = serializers.SerializerMethodField()
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
                "codigo_barra": item.producto.codigo_barra,
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
