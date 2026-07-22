from django.contrib import admin

from .models import BannerPromocional


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
