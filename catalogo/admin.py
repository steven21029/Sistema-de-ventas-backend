from django.contrib import admin

from .models import Categoria, Familia, PaqueteCatalogo, PaqueteProducto, Producto


@admin.register(Familia)
class FamiliaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "empresa", "activa", "orden", "fecha_creacion")
    list_filter = ("empresa", "activa")
    search_fields = ("nombre", "empresa__nombre")
    readonly_fields = ("orden", "fecha_creacion", "fecha_actualizacion")
    ordering = ("empresa__nombre", "orden", "nombre")
    fieldsets = (
        (
            "Familia",
            {
                "fields": (
                    "empresa",
                    "nombre",
                    "descripcion",
                    "imagen",
                    "imagen_url",
                    "activa",
                )
            },
        ),
        (
            "Orden automatico",
            {
                "fields": (
                    "orden",
                )
            },
        ),
        (
            "Fechas",
            {
                "fields": (
                    "fecha_creacion",
                    "fecha_actualizacion",
                )
            },
        ),
    )


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "familia", "empresa", "activa", "orden", "fecha_creacion")
    list_filter = ("empresa", "familia", "activa")
    search_fields = ("nombre", "familia__nombre", "empresa__nombre")
    autocomplete_fields = ("empresa", "familia")
    readonly_fields = ("orden", "fecha_creacion", "fecha_actualizacion")
    ordering = ("empresa__nombre", "familia__orden", "orden", "nombre")
    fieldsets = (
        (
            "Categoria",
            {
                "fields": (
                    "empresa",
                    "familia",
                    "nombre",
                    "descripcion",
                    "activa",
                )
            },
        ),
        (
            "Orden automatico",
            {
                "fields": (
                    "orden",
                )
            },
        ),
        (
            "Fechas",
            {
                "fields": (
                    "fecha_creacion",
                    "fecha_actualizacion",
                )
            },
        ),
    )


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "codigo_barra",
        "empresa",
        "familia",
        "categoria",
        "precio",
        "existencia",
        "existencia_minima",
        "orden_destacado",
        "activo",
    )
    list_filter = ("empresa", "familia", "categoria", "activo")
    search_fields = ("nombre", "codigo_barra", "empresa__nombre")
    autocomplete_fields = ("empresa", "familia", "categoria")
    readonly_fields = ("existencia", "fecha_creacion", "fecha_actualizacion")
    ordering = ("empresa__nombre", "nombre")

    fieldsets = (
        (
            "Empresa y clasificacion",
            {
                "fields": (
                    "empresa",
                    "familia",
                    "categoria",
                )
            },
        ),
        (
            "Producto",
            {
                "fields": (
                    "codigo_barra",
                    "nombre",
                    "descripcion",
                    "imagen_principal",
                    "imagen_url",
                )
            },
        ),
        (
            "Venta e inventario actual",
            {
                "fields": (
                    "precio",
                    "existencia",
                    "existencia_minima",
                    "orden_destacado",
                    "activo",
                )
            },
        ),
        (
            "Fechas",
            {
                "fields": (
                    "fecha_creacion",
                    "fecha_actualizacion",
                )
            },
        ),
    )


class PaqueteProductoInline(admin.TabularInline):
    model = PaqueteProducto
    extra = 0
    autocomplete_fields = ("producto",)
    fields = ("producto", "orden")


@admin.register(PaqueteCatalogo)
class PaqueteCatalogoAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "codigo",
        "tipo",
        "empresa",
        "precio_normal",
        "precio_paquete",
        "porcentaje_descuento",
        "destacado",
        "activo",
        "orden",
    )
    list_filter = ("empresa", "tipo", "destacado", "activo")
    search_fields = ("nombre", "codigo", "descripcion", "empresa__nombre")
    autocomplete_fields = ("empresa",)
    readonly_fields = ("fecha_creacion", "fecha_actualizacion")
    ordering = ("empresa__nombre", "tipo", "orden", "nombre")
    inlines = [PaqueteProductoInline]

    fieldsets = (
        (
            "Empresa y tipo",
            {
                "fields": (
                    "empresa",
                    "tipo",
                    "codigo",
                )
            },
        ),
        (
            "Contenido",
            {
                "fields": (
                    "nombre",
                    "descripcion",
                    "imagen",
                    "imagen_url",
                )
            },
        ),
        (
            "Precio",
            {
                "fields": (
                    "precio_normal",
                    "precio_paquete",
                    "porcentaje_descuento",
                )
            },
        ),
        (
            "Publicacion",
            {
                "fields": (
                    "destacado",
                    "activo",
                    "orden",
                )
            },
        ),
        (
            "Fechas",
            {
                "fields": (
                    "fecha_creacion",
                    "fecha_actualizacion",
                )
            },
        ),
    )


@admin.register(PaqueteProducto)
class PaqueteProductoAdmin(admin.ModelAdmin):
    list_display = ("paquete", "producto", "orden")
    list_filter = ("paquete__empresa", "paquete__tipo")
    search_fields = (
        "paquete__nombre",
        "paquete__codigo",
        "producto__nombre",
        "producto__codigo_barra",
    )
    autocomplete_fields = ("paquete", "producto")
