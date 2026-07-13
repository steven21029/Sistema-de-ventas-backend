from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import PerfilUsuario

User = get_user_model()


class UsuarioBasicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_superuser",
        ]
        read_only_fields = fields


class PerfilUsuarioSerializer(serializers.ModelSerializer):
    usuario_detalle = UsuarioBasicoSerializer(source="usuario", read_only=True)
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    rol_nombre = serializers.CharField(source="get_rol_display", read_only=True)

    class Meta:
        model = PerfilUsuario
        fields = [
            "id",
            "usuario",
            "usuario_detalle",
            "empresa",
            "empresa_nombre",
            "rol",
            "rol_nombre",
            "telefono",
            "correo_verificado",
            "puede_crear_usuarios",
            "activo",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id",
            "usuario_detalle",
            "empresa_nombre",
            "rol_nombre",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
