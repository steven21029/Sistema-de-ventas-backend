from rest_framework import serializers

from .models import Empresa


class EmpresaSerializer(serializers.ModelSerializer):
    creada_por = serializers.StringRelatedField(read_only=True)

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
            "activa",
            "creada_por",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id",
            "slug",
            "creada_por",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
