from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import (
    Empresa,
    MENU_PREDETERMINADO,
    ItemMenuEmpresa,
    SobreNosotrosEmpresa,
    SucursalEmpresa,
)


def dividir_horario_en_lineas(horario):
    if not horario:
        return []

    partes = horario.replace("\r\n", "\n").replace("\r", "\n").replace(";", "\n")
    return [linea.strip() for linea in partes.splitlines() if linea.strip()]


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


class ItemMenuEmpresaAdminSerializer(serializers.ModelSerializer):
    empresa = serializers.PrimaryKeyRelatedField(read_only=True)
    orden = serializers.IntegerField(min_value=1, required=False)

    class Meta:
        model = ItemMenuEmpresa
        fields = [
            "id",
            "empresa",
            "clave",
            "texto",
            "ruta",
            "orden",
            "activo",
            "abre_en_nueva_pestana",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id",
            "empresa",
            "clave",
            "ruta",
            "abre_en_nueva_pestana",
            "fecha_creacion",
            "fecha_actualizacion",
        ]

    def validate(self, attrs):
        empresa = self.context.get("empresa") or getattr(
            self.instance,
            "empresa",
            None,
        )
        orden = attrs.get("orden", getattr(self.instance, "orden", None))

        if empresa and orden:
            repetido = ItemMenuEmpresa.objects.filter(
                empresa=empresa,
                orden=orden,
            )
            if self.instance:
                repetido = repetido.exclude(pk=self.instance.pk)
            if repetido.exists():
                raise serializers.ValidationError(
                    {"orden": "Ya existe un item con este orden en la empresa."}
                )

        return attrs


class SobreNosotrosEmpresaSerializer(serializers.ModelSerializer):
    empresa = serializers.PrimaryKeyRelatedField(read_only=True)
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    empresa_slug = serializers.CharField(source="empresa.slug", read_only=True)
    imagen_final = serializers.SerializerMethodField()
    valores_lista = serializers.ListField(read_only=True)

    class Meta:
        model = SobreNosotrosEmpresa
        fields = [
            "id",
            "empresa",
            "empresa_nombre",
            "empresa_slug",
            "titulo",
            "introduccion",
            "historia",
            "mision",
            "vision",
            "valores",
            "valores_lista",
            "compromiso",
            "imagen",
            "imagen_url",
            "imagen_final",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id",
            "empresa",
            "empresa_nombre",
            "empresa_slug",
            "valores_lista",
            "imagen_final",
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


class SobreNosotrosEmpresaPublicoSerializer(SobreNosotrosEmpresaSerializer):
    class Meta(SobreNosotrosEmpresaSerializer.Meta):
        fields = [
            "titulo",
            "introduccion",
            "historia",
            "mision",
            "vision",
            "valores_lista",
            "compromiso",
            "imagen_final",
        ]
        read_only_fields = fields


class EmpresaSerializer(serializers.ModelSerializer):
    creada_por = serializers.StringRelatedField(read_only=True)
    opciones_entrega_disponibles = serializers.ListField(read_only=True)
    modo_inventario_nombre = serializers.CharField(
        source="get_modo_inventario_display",
        read_only=True,
    )
    pago_en_linea_proveedor_nombre = serializers.CharField(
        source="get_pago_en_linea_proveedor_display",
        read_only=True,
    )
    pago_en_linea_modo_nombre = serializers.CharField(
        source="get_pago_en_linea_modo_display",
        read_only=True,
    )
    pago_en_linea_disponible = serializers.BooleanField(read_only=True)
    pago_en_linea_credencial_secreta = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        trim_whitespace=True,
    )
    pago_en_linea_webhook_secreto = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        trim_whitespace=True,
    )
    pago_en_linea_credencial_secreta_configurada = serializers.SerializerMethodField()
    pago_en_linea_webhook_secreto_configurado = serializers.SerializerMethodField()
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
            "instagram_url",
            "whatsapp_url",
            "facebook_url",
            "tiktok_url",
            "tiene_envios",
            "cobra_impuesto",
            "pago_en_linea_activo",
            "pago_en_linea_disponible",
            "pago_en_linea_proveedor",
            "pago_en_linea_proveedor_nombre",
            "pago_en_linea_modo",
            "pago_en_linea_modo_nombre",
            "pago_en_linea_credencial_publica",
            "pago_en_linea_credencial_secreta",
            "pago_en_linea_credencial_secreta_configurada",
            "pago_en_linea_webhook_secreto",
            "pago_en_linea_webhook_secreto_configurado",
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

    def get_pago_en_linea_credencial_secreta_configurada(self, obj):
        return bool((obj.pago_en_linea_credencial_secreta or "").strip())

    def get_pago_en_linea_webhook_secreto_configurado(self, obj):
        return bool((obj.pago_en_linea_webhook_secreto or "").strip())

    def get_imagen_sucursales_final(self, obj):
        if obj.imagen_sucursales_url:
            return obj.imagen_sucursales_url

        if not obj.imagen_sucursales:
            return None

        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.imagen_sucursales.url)

        return obj.imagen_sucursales.url

    def validate(self, attrs):
        valores = {}
        for campo in [
            "pago_en_linea_activo",
            "pago_en_linea_proveedor",
            "pago_en_linea_credencial_publica",
            "pago_en_linea_credencial_secreta",
            "pago_en_linea_webhook_secreto",
        ]:
            if campo in attrs:
                valores[campo] = attrs[campo]
            elif self.instance:
                valores[campo] = getattr(self.instance, campo)
            else:
                valores[campo] = Empresa._meta.get_field(campo).get_default()

        try:
            Empresa.validar_configuracion_pago_en_linea(
                activo=valores["pago_en_linea_activo"],
                proveedor=valores["pago_en_linea_proveedor"],
                credencial_publica=valores["pago_en_linea_credencial_publica"],
                credencial_secreta=valores["pago_en_linea_credencial_secreta"],
                webhook_secreto=valores["pago_en_linea_webhook_secreto"],
            )
        except DjangoValidationError as exc:
            if hasattr(exc, "message_dict"):
                raise serializers.ValidationError(exc.message_dict) from exc
            raise serializers.ValidationError(exc.messages) from exc

        return attrs


class EmpresaMiEmpresaSerializer(EmpresaSerializer):
    class Meta(EmpresaSerializer.Meta):
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
            "instagram_url",
            "whatsapp_url",
            "facebook_url",
            "tiktok_url",
            "tiene_envios",
            "cobra_impuesto",
            "pago_en_linea_activo",
            "pago_en_linea_disponible",
            "pago_en_linea_proveedor",
            "pago_en_linea_proveedor_nombre",
            "pago_en_linea_modo",
            "pago_en_linea_modo_nombre",
            "pago_en_linea_credencial_publica",
            "pago_en_linea_credencial_secreta",
            "pago_en_linea_credencial_secreta_configurada",
            "pago_en_linea_webhook_secreto",
            "pago_en_linea_webhook_secreto_configurado",
            "productos_con_imagen",
            "opciones_entrega_disponibles",
            "modo_inventario",
            "modo_inventario_nombre",
            "permite_productos_fisicos",
            "permite_servicios",
            "activa",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id",
            "slug",
            "subdominio",
            "dominio_personalizado",
            "imagen_sucursales_final",
            "pago_en_linea_disponible",
            "pago_en_linea_proveedor_nombre",
            "pago_en_linea_modo_nombre",
            "pago_en_linea_credencial_secreta_configurada",
            "pago_en_linea_webhook_secreto_configurado",
            "opciones_entrega_disponibles",
            "modo_inventario",
            "modo_inventario_nombre",
            "permite_productos_fisicos",
            "permite_servicios",
            "activa",
            "fecha_creacion",
            "fecha_actualizacion",
        ]


class EmpresaPublicaSerializer(serializers.ModelSerializer):
    opciones_entrega_disponibles = serializers.ListField(read_only=True)
    modo_inventario_nombre = serializers.CharField(
        source="get_modo_inventario_display",
        read_only=True,
    )
    pago_en_linea_disponible = serializers.BooleanField(read_only=True)
    permite_productos_fisicos = serializers.BooleanField(read_only=True)
    permite_servicios = serializers.BooleanField(read_only=True)
    menu = serializers.SerializerMethodField()
    imagen_sucursales_final = serializers.SerializerMethodField()
    redes_sociales = serializers.SerializerMethodField()

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
            "redes_sociales",
            "tiene_envios",
            "cobra_impuesto",
            "pago_en_linea_disponible",
            "pago_en_linea_proveedor",
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

    def get_redes_sociales(self, obj):
        return {
            "instagram_url": obj.instagram_url,
            "whatsapp_url": obj.whatsapp_url,
            "facebook_url": obj.facebook_url,
            "tiktok_url": obj.tiktok_url,
        }


class SucursalEmpresaPublicaSerializer(serializers.ModelSerializer):
    imagen_final = serializers.SerializerMethodField()
    horario_lineas = serializers.SerializerMethodField()

    class Meta:
        model = SucursalEmpresa
        fields = [
            "id",
            "nombre",
            "ciudad",
            "direccion",
            "telefono",
            "horario",
            "horario_lineas",
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

    def get_horario_lineas(self, obj):
        return dividir_horario_en_lineas(obj.horario)


class SucursalEmpresaAdminSerializer(serializers.ModelSerializer):
    empresa = serializers.PrimaryKeyRelatedField(read_only=True)
    imagen_final = serializers.SerializerMethodField()
    horario_lineas = serializers.SerializerMethodField()
    orden = serializers.IntegerField(min_value=1, required=False)

    class Meta:
        model = SucursalEmpresa
        fields = [
            "id",
            "empresa",
            "nombre",
            "ciudad",
            "direccion",
            "telefono",
            "horario",
            "horario_lineas",
            "google_maps_url",
            "imagen",
            "imagen_url",
            "imagen_final",
            "latitud",
            "longitud",
            "orden",
            "activa",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id",
            "empresa",
            "imagen_final",
            "fecha_creacion",
            "fecha_actualizacion",
        ]

    def get_imagen_final(self, obj):
        if not obj.imagen_final:
            return None

        if str(obj.imagen_final).startswith(("http://", "https://")):
            return obj.imagen_final

        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.imagen_final)
        return obj.imagen_final

    def get_horario_lineas(self, obj):
        return dividir_horario_en_lineas(obj.horario)
