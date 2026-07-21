from rest_framework import serializers

from .models import Empresa


class EmpresaSerializer(serializers.ModelSerializer):
    creada_por = serializers.StringRelatedField(read_only=True)
    opciones_entrega_disponibles = serializers.ListField(read_only=True)

    class Meta:
        model = Empresa
        fields = [
            "id",
            "nombre",
            "slug",
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

    class Meta:
        model = Empresa
        fields = [
            "nombre",
            "slug",
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
        ]
        read_only_fields = fields
        read_only_fields = [
            "id",
            "slug",
            "opciones_entrega_disponibles",
            "creada_por",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
