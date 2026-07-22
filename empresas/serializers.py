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

    class Meta:
        model = Empresa
        fields = [
            "id",
            "nombre",
            "slug",
            "subdominio",
            "dominio_personalizado",
            "logo",
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
            "opciones_entrega_disponibles",
            "activa",
            "creada_por",
            "fecha_creacion",
            "fecha_actualizacion",
        ]


class EmpresaPublicaSerializer(serializers.ModelSerializer):
    opciones_entrega_disponibles = serializers.ListField(read_only=True)
    menu = serializers.SerializerMethodField()

    class Meta:
        model = Empresa
        fields = [
            "nombre",
            "slug",
            "subdominio",
            "dominio_personalizado",
            "logo",
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
            "opciones_entrega_disponibles",
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


class SucursalEmpresaPublicaSerializer(serializers.ModelSerializer):
    class Meta:
        model = SucursalEmpresa
        fields = [
            "nombre",
            "direccion",
            "telefono",
            "horario",
            "google_maps_url",
            "latitud",
            "longitud",
            "orden",
        ]
        read_only_fields = fields
