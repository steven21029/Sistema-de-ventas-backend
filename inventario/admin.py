from django.contrib import admin

from .models import MovimientoInventario


@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = (
        "producto",
        "empresa",
        "tipo",
        "cantidad",
        "existencia_anterior",
        "existencia_nueva",
        "usuario",
        "fecha_creacion",
    )
    list_filter = ("empresa", "tipo", "fecha_creacion")
    search_fields = (
        "producto__nombre",
        "producto__codigo_barra",
        "empresa__nombre",
        "motivo",
        "referencia",
    )
    autocomplete_fields = ("empresa", "producto", "usuario")
    readonly_fields = (
        "existencia_anterior",
        "existencia_nueva",
        "usuario",
        "fecha_creacion",
    )
    ordering = ("-fecha_creacion", "-id")

    fieldsets = (
        (
            "Movimiento",
            {
                "fields": (
                    "empresa",
                    "producto",
                    "tipo",
                    "cantidad",
                    "motivo",
                    "referencia",
                )
            },
        ),
        (
            "Resultado",
            {
                "fields": (
                    "existencia_anterior",
                    "existencia_nueva",
                )
            },
        ),
        (
            "Auditoria",
            {
                "fields": (
                    "usuario",
                    "fecha_creacion",
                )
            },
        ),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return tuple(field.name for field in self.model._meta.fields)

        return self.readonly_fields

    def save_model(self, request, obj, form, change):
        if not obj.usuario_id and request.user.is_authenticated:
            obj.usuario = request.user
        super().save_model(request, obj, form, change)
