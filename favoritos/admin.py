from django.contrib import admin

from .models import Favorito


@admin.register(Favorito)
class FavoritoAdmin(admin.ModelAdmin):
    list_display = ("usuario", "empresa", "producto", "fecha_creacion")
    list_filter = ("empresa", "fecha_creacion")
    search_fields = (
        "usuario__username",
        "usuario__email",
        "empresa__nombre",
        "producto__nombre",
        "producto__codigo_barra",
    )
    autocomplete_fields = ("empresa", "usuario", "producto")
    readonly_fields = ("fecha_creacion",)
