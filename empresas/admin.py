from django.contrib import admin

from .models import Empresa, ItemMenuEmpresa, SucursalEmpresa


class ItemMenuEmpresaInline(admin.TabularInline):
    model = ItemMenuEmpresa
    extra = 0
    fields = (
        "clave",
        "texto",
        "ruta",
        "orden",
        "activo",
        "abre_en_nueva_pestana",
    )


class SucursalEmpresaInline(admin.TabularInline):
    model = SucursalEmpresa
    extra = 0
    fields = (
        "nombre",
        "telefono",
        "horario",
        "google_maps_url",
        "orden",
        "activa",
    )


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
        "productos_con_imagen",
        "activa",
        "fecha_creacion",
    )
    list_filter = (
        "modo_inventario",
        "tiene_envios",
        "cobra_impuesto",
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
    autocomplete_fields = ("empresa",)
    readonly_fields = ("fecha_creacion", "fecha_actualizacion")
    ordering = ("empresa__nombre", "orden", "texto")


@admin.register(SucursalEmpresa)
class SucursalEmpresaAdmin(admin.ModelAdmin):
    exclude = ("imagen", "imagen_url")
    list_display = (
        "nombre",
        "empresa",
        "telefono",
        "horario",
        "orden",
        "activa",
    )
    list_filter = ("empresa", "activa")
    search_fields = ("nombre", "direccion", "telefono", "empresa__nombre")
    autocomplete_fields = ("empresa",)
    readonly_fields = ("fecha_creacion", "fecha_actualizacion")
    ordering = ("empresa__nombre", "orden", "nombre")
