from rest_framework import serializers

from .models import Empresa, MENU_PREDETERMINADO, ItemMenuEmpresa, SucursalEmpresa


class ItemMenuEmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemMenuEmpresa
        fields = [
            "clave",
            "texto",
            "ruta",
            "orden",
            "activo",
            "abre_en_nueva_pestana",
        ]
        read_only_fields = fields


class EmpresaSerializer(serializers.ModelSerializer):
    creada_por = serializers.StringRelatedField(read_only=True)
    opciones_entrega_disponibles = serializers.ListField(read_only=True)
    modo_inventario_nombre = serializers.CharField(
        source="get_modo_inventario_display",
        read_only=True,
    )
    permite_productos_fisicos = serializers.BooleanField(read_only=True)
    permite_servicios = serializers.BooleanField(read_only=True)
    imagen_sucursales_final = serializers.SerializerMethodField()

    class Meta:
        model = Empresa
        fields = [
            "id",
            "nombre",
            "slug",
            "subdominio",
            "dominio_personalizado",
            "logo",
            "imagen_sucursales",
            "imagen_sucursales_url",
            "imagen_sucursales_final",
            "color_principal",
            "color_secundario",
            "color_acento",
            "color_texto",
            "color_fondo",
            "telefono",
            "correo",
            "direccion",
            "sitio_web",
            "tiene_envios",
            "cobra_impuesto",
            "productos_con_imagen",
            "opciones_entrega_disponibles",
            "modo_inventario",
            "modo_inventario_nombre",
            "permite_productos_fisicos",
            "permite_servicios",
            "activa",
            "creada_por",
            "fecha_creacion",
            "fecha_actualizacion",
        ]

    def get_imagen_sucursales_final(self, obj):
        if obj.imagen_sucursales_url:
            return obj.imagen_sucursales_url

        if not obj.imagen_sucursales:
            return None

        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.imagen_sucursales.url)

        return obj.imagen_sucursales.url


class EmpresaPublicaSerializer(serializers.ModelSerializer):
    opciones_entrega_disponibles = serializers.ListField(read_only=True)
    modo_inventario_nombre = serializers.CharField(
        source="get_modo_inventario_display",
        read_only=True,
    )
    permite_productos_fisicos = serializers.BooleanField(read_only=True)
    permite_servicios = serializers.BooleanField(read_only=True)
    menu = serializers.SerializerMethodField()
    imagen_sucursales_final = serializers.SerializerMethodField()

    class Meta:
        model = Empresa
        fields = [
            "nombre",
            "slug",
            "subdominio",
            "dominio_personalizado",
            "logo",
            "imagen_sucursales_url",
            "imagen_sucursales_final",
            "color_principal",
            "color_secundario",
            "color_acento",
            "color_texto",
            "color_fondo",
            "telefono",
            "correo",
            "direccion",
            "sitio_web",
            "tiene_envios",
            "cobra_impuesto",
            "productos_con_imagen",
            "opciones_entrega_disponibles",
            "modo_inventario",
            "modo_inventario_nombre",
            "permite_productos_fisicos",
            "permite_servicios",
            "menu",
        ]
        read_only_fields = fields

    def get_menu(self, obj):
        items_menu = obj.items_menu.all()
        if not items_menu.exists():
            return [
                {
                    "clave": clave,
                    "texto": texto,
                    "ruta": ruta,
                    "orden": orden,
                    "activo": True,
                    "abre_en_nueva_pestana": False,
                }
                for clave, texto, ruta, orden in MENU_PREDETERMINADO
            ]

        items_activos = items_menu.filter(activo=True).order_by("orden", "texto")
        return ItemMenuEmpresaSerializer(items_activos, many=True).data

    def get_imagen_sucursales_final(self, obj):
        if obj.imagen_sucursales_url:
            return obj.imagen_sucursales_url

        if not obj.imagen_sucursales:
            return None

        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.imagen_sucursales.url)

        return obj.imagen_sucursales.url


class SucursalEmpresaPublicaSerializer(serializers.ModelSerializer):
    imagen_final = serializers.SerializerMethodField()

    class Meta:
        model = SucursalEmpresa
        fields = [
            "nombre",
            "direccion",
            "telefono",
            "horario",
            "google_maps_url",
            "imagen_final",
            "latitud",
            "longitud",
            "orden",
        ]
        read_only_fields = fields

    def get_imagen_final(self, obj):
        if obj.empresa.imagen_sucursales_url:
            return obj.empresa.imagen_sucursales_url

        if obj.empresa.imagen_sucursales:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.empresa.imagen_sucursales.url)

            return obj.empresa.imagen_sucursales.url

        return None
