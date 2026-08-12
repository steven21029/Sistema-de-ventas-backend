from django.contrib import admin

from .models import (
    Departamento,
    Empresa,
    ItemMenuEmpresa,
    Municipio,
    SobreNosotrosEmpresa,
    SucursalEmpresa,
)


class ItemMenuEmpresaInline(admin.TabularInline):
    model = ItemMenuEmpresa
    extra = 0
    can_delete = False
    fields = (
        "clave",
        "texto",
        "ruta",
        "orden",
        "activo",
        "abre_en_nueva_pestana",
    )
    readonly_fields = ("clave", "ruta", "abre_en_nueva_pestana")

    def has_add_permission(self, request, obj=None):
        return False


class SucursalEmpresaInline(admin.TabularInline):
    model = SucursalEmpresa
    extra = 0
    fields = (
        "nombre",
        "municipio",
        "ciudad",
        "telefono",
        "horario",
        "google_maps_url",
        "orden",
        "estado",
        "activa",
    )
    readonly_fields = ("ciudad",)


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "slug",
        "subdominio",
        "dominio_personalizado",
        "correo",
        "telefono",
        "modo_inventario",
        "tiene_envios",
        "cobra_impuesto",
        "pago_en_linea_activo",
        "pago_en_linea_proveedor",
        "productos_con_imagen",
        "activa",
        "fecha_creacion",
    )
    list_filter = (
        "modo_inventario",
        "tiene_envios",
        "cobra_impuesto",
        "pago_en_linea_activo",
        "pago_en_linea_proveedor",
        "pago_en_linea_modo",
        "productos_con_imagen",
        "activa",
        "fecha_creacion",
    )
    search_fields = (
        "nombre",
        "slug",
        "subdominio",
        "dominio_personalizado",
        "correo",
        "telefono",
    )
    prepopulated_fields = {"slug": ("nombre",)}
    readonly_fields = ("creada_por", "fecha_creacion", "fecha_actualizacion")
    inlines = [ItemMenuEmpresaInline, SucursalEmpresaInline]

    fieldsets = (
        (
            "Identidad",
            {
                "fields": (
                    "nombre",
                    "slug",
                    "subdominio",
                    "dominio_personalizado",
                    "logo",
                )
            },
        ),
        (
            "Configuracion visual",
            {
                "fields": (
                    "color_principal",
                    "color_secundario",
                    "color_acento",
                    "color_texto",
                    "color_fondo",
                )
            },
        ),
        (
            "Sucursales",
            {
                "fields": (
                    "imagen_sucursales",
                    "imagen_sucursales_url",
                )
            },
        ),
        (
            "Contacto",
            {
                "fields": (
                    "telefono",
                    "correo",
                    "direccion",
                    "sitio_web",
                )
            },
        ),
        (
            "Redes sociales",
            {
                "fields": (
                    "instagram_url",
                    "whatsapp_url",
                    "facebook_url",
                    "tiktok_url",
                )
            },
        ),
        (
            "Operación",
            {
                "fields": (
                    "modo_inventario",
                    "tiene_envios",
                    "cobra_impuesto",
                    "productos_con_imagen",
                )
            },
        ),
        (
            "Pagos en linea",
            {
                "fields": (
                    "pago_en_linea_activo",
                    "pago_en_linea_proveedor",
                    "pago_en_linea_modo",
                    "pago_en_linea_credencial_publica",
                    "pago_en_linea_credencial_secreta",
                    "pago_en_linea_webhook_secreto",
                )
            },
        ),
        (
            "Control",
            {
                "fields": (
                    "activa",
                    "creada_por",
                    "fecha_creacion",
                    "fecha_actualizacion",
                )
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        if not obj.creada_por_id and request.user.is_authenticated:
            obj.creada_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(ItemMenuEmpresa)
class ItemMenuEmpresaAdmin(admin.ModelAdmin):
    list_display = (
        "texto",
        "clave",
        "empresa",
        "ruta",
        "orden",
        "activo",
        "abre_en_nueva_pestana",
    )
    list_filter = ("empresa", "activo", "abre_en_nueva_pestana")
    search_fields = ("texto", "clave", "ruta", "empresa__nombre", "empresa__slug")
    readonly_fields = (
        "empresa",
        "clave",
        "ruta",
        "abre_en_nueva_pestana",
        "fecha_creacion",
        "fecha_actualizacion",
    )
    ordering = ("empresa__nombre", "orden", "texto")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SobreNosotrosEmpresa)
class SobreNosotrosEmpresaAdmin(admin.ModelAdmin):
    list_display = ("empresa", "titulo", "fecha_actualizacion")
    search_fields = ("empresa__nombre", "empresa__slug", "titulo")
    readonly_fields = ("empresa", "fecha_creacion", "fecha_actualizacion")
    fieldsets = (
        (
            "Empresa",
            {
                "fields": (
                    "empresa",
                    "titulo",
                    "introduccion",
                    "historia",
                )
            },
        ),
        (
            "Identidad",
            {"fields": ("mision", "vision", "valores", "compromiso")},
        ),
        (
            "Imagen",
            {"fields": ("imagen", "imagen_url")},
        ),
        (
            "Control",
            {"fields": ("fecha_creacion", "fecha_actualizacion")},
        ),
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Departamento)
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "codigo",
        "orden",
        "activo",
        "fecha_actualizacion",
    )
    list_filter = ("activo",)
    search_fields = ("nombre", "codigo")
    readonly_fields = ("fecha_creacion", "fecha_actualizacion")
    ordering = ("orden", "nombre")


@admin.register(Municipio)
class MunicipioAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "departamento",
        "codigo",
        "orden",
        "activo",
        "fecha_actualizacion",
    )
    list_filter = ("departamento", "activo")
    search_fields = ("nombre", "codigo", "departamento__nombre")
    autocomplete_fields = ("departamento",)
    readonly_fields = ("nombre_normalizado", "fecha_creacion", "fecha_actualizacion")
    ordering = ("departamento__orden", "nombre")


@admin.register(SucursalEmpresa)
class SucursalEmpresaAdmin(admin.ModelAdmin):
    exclude = ("imagen", "imagen_url")
    list_display = (
        "nombre",
        "empresa",
        "municipio",
        "ciudad",
        "telefono",
        "horario",
        "orden",
        "estado",
        "activa",
    )
    list_filter = ("empresa", "municipio", "municipio__departamento", "estado", "activa")
    search_fields = (
        "nombre",
        "ciudad",
        "municipio__nombre",
        "municipio__departamento__nombre",
        "direccion",
        "telefono",
        "empresa__nombre",
    )
    autocomplete_fields = ("empresa", "municipio")
    readonly_fields = ("fecha_creacion", "fecha_actualizacion")
    ordering = ("empresa__nombre", "orden", "nombre")
