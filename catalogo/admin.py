from django.contrib import admin

from .models import Categoria, Familia, Producto


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
        "activo",
    )
    list_filter = ("empresa", "familia", "categoria", "activo")
    search_fields = ("nombre", "codigo_barra", "empresa__nombre")
    autocomplete_fields = ("empresa", "familia", "categoria")
    readonly_fields = ("fecha_creacion", "fecha_actualizacion")
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
                )
            },
        ),
        (
            "Venta e inventario inicial",
            {
                "fields": (
                    "precio",
                    "existencia",
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
