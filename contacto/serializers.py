from rest_framework import serializers

from empresas.models import Empresa
from .models import MensajeContacto


class MensajeContactoCreateSerializer(serializers.ModelSerializer):
    empresa_slug = serializers.CharField(write_only=True)

    class Meta:
        model = MensajeContacto
        fields = [
            "empresa_slug",
            "nombre",
            "telefono",
            "correo",
            "asunto",
            "mensaje",
        ]

    def validate(self, attrs):
        empresa_slug = attrs.get("empresa_slug", "").strip()
        if not empresa_slug:
            raise serializers.ValidationError(
                {"empresa_slug": "Debes enviar el slug de la empresa."}
            )

        empresa = Empresa.objects.filter(slug__iexact=empresa_slug, activa=True).first()
        if not empresa:
            raise serializers.ValidationError(
                {"empresa_slug": "La empresa no existe o no esta activa."}
            )

        nombre = attrs.get("nombre", "").strip()
        mensaje = attrs.get("mensaje", "").strip()
        telefono = attrs.get("telefono", "").strip()
        correo = attrs.get("correo", "").strip()

        if not nombre:
            raise serializers.ValidationError({"nombre": "Este campo es obligatorio."})

        if not mensaje:
            raise serializers.ValidationError({"mensaje": "Este campo es obligatorio."})

        if not telefono and not correo:
            raise serializers.ValidationError(
                {"contacto": "Debes enviar telefono o correo."}
            )

        attrs["empresa"] = empresa
        attrs.pop("empresa_slug", None)
        return attrs


class MensajeContactoAdminSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    empresa_slug = serializers.CharField(source="empresa.slug", read_only=True)
    estado_nombre = serializers.CharField(source="get_estado_display", read_only=True)

    class Meta:
        model = MensajeContacto
        fields = [
            "id",
            "empresa",
            "empresa_nombre",
            "empresa_slug",
            "nombre",
            "telefono",
            "correo",
            "asunto",
            "mensaje",
            "estado",
            "estado_nombre",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id",
            "empresa",
            "empresa_nombre",
            "empresa_slug",
            "nombre",
            "telefono",
            "correo",
            "asunto",
            "mensaje",
            "estado_nombre",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
