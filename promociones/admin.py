from django.contrib import admin

from .models import BannerPromocional, OfertaProducto, OfertaPromocional


@admin.register(BannerPromocional)
class BannerPromocionalAdmin(admin.ModelAdmin):
    list_display = (
        "titulo",
        "empresa",
        "orden",
        "activo",
        "esta_vigente",
        "fecha_inicio",
        "fecha_fin",
    )
    list_filter = ("empresa", "activo", "fecha_inicio", "fecha_fin")
    search_fields = ("titulo", "subtitulo", "empresa__nombre", "empresa__slug")
    autocomplete_fields = ("empresa",)
    readonly_fields = ("fecha_creacion", "fecha_actualizacion")

    fieldsets = (
        (
            "Empresa y contenido",
            {
                "fields": (
                    "empresa",
                    "titulo",
                    "subtitulo",
                    "texto_boton",
                    "url_boton",
                    "texto_alternativo",
                )
            },
        ),
        (
            "Imagen",
            {
                "fields": (
                    "imagen",
                    "imagen_url",
                )
            },
        ),
        (
            "Publicacion",
            {
                "fields": (
                    "orden",
                    "activo",
                    "fecha_inicio",
                    "fecha_fin",
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


class OfertaProductoInline(admin.TabularInline):
    model = OfertaProducto
    extra = 0
    autocomplete_fields = ("producto",)
    fields = ("producto", "orden")


@admin.register(OfertaPromocional)
class OfertaPromocionalAdmin(admin.ModelAdmin):
    list_display = (
        "titulo",
        "codigo",
        "tipo",
        "empresa",
        "precio_normal",
        "precio_oferta",
        "porcentaje_descuento",
        "activo",
        "esta_vigente",
        "orden",
    )
    list_filter = ("empresa", "tipo", "activo", "fecha_inicio", "fecha_fin")
    search_fields = (
        "titulo",
        "codigo",
        "descripcion",
        "empresa__nombre",
        "empresa__slug",
        "paquete__nombre",
        "paquete__codigo",
    )
    autocomplete_fields = ("empresa", "paquete")
    readonly_fields = ("fecha_creacion", "fecha_actualizacion")
    ordering = ("empresa__nombre", "orden", "titulo")
    inlines = [OfertaProductoInline]

    fieldsets = (
        (
            "Empresa y tipo",
            {
                "fields": (
                    "empresa",
                    "tipo",
                    "codigo",
                    "paquete",
                )
            },
        ),
        (
            "Contenido",
            {
                "fields": (
                    "titulo",
                    "descripcion",
                    "url_destino",
                )
            },
        ),
        (
            "Precio",
            {
                "fields": (
                    "precio_normal",
                    "precio_oferta",
                    "porcentaje_descuento",
                )
            },
        ),
        (
            "Imagen",
            {
                "fields": (
                    "imagen",
                    "imagen_url",
                )
            },
        ),
        (
            "Publicacion",
            {
                "fields": (
                    "orden",
                    "activo",
                    "fecha_inicio",
                    "fecha_fin",
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


@admin.register(OfertaProducto)
class OfertaProductoAdmin(admin.ModelAdmin):
    list_display = ("oferta", "producto", "orden")
    list_filter = ("oferta__empresa", "oferta__tipo")
    search_fields = (
        "oferta__titulo",
        "oferta__codigo",
        "producto__nombre",
        "producto__codigo_barra",
    )
    autocomplete_fields = ("oferta", "producto")
