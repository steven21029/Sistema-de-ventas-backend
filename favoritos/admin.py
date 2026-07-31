from django.contrib import admin

from .models import Favorito


@admin.register(Favorito)
class FavoritoAdmin(admin.ModelAdmin):
    list_display = (
        "usuario",
        "empresa",
        "tipo",
        "articulo_favorito",
        "fecha_creacion",
    )
    list_filter = ("empresa", "paquete__tipo", "fecha_creacion")
    search_fields = (
        "usuario__username",
        "usuario__email",
        "empresa__nombre",
        "producto__nombre",
        "producto__codigo_interno",
        "producto__codigo_barra",
        "paquete__nombre",
        "paquete__codigo",
    )
    autocomplete_fields = ("empresa", "usuario", "producto", "paquete")
    readonly_fields = ("fecha_creacion",)

    @admin.display(description="Tipo")
    def tipo(self, obj):
        return obj.tipo_articulo

    @admin.display(description="Articulo")
    def articulo_favorito(self, obj):
        return obj.articulo
