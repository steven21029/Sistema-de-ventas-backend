from django.contrib import admin

from .models import Empresa


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "slug",
        "correo",
        "telefono",
        "activa",
        "fecha_creacion",
    )
    list_filter = ("activa", "fecha_creacion")
    search_fields = ("nombre", "slug", "correo", "telefono")
    prepopulated_fields = {"slug": ("nombre",)}
    readonly_fields = ("creada_por", "fecha_creacion", "fecha_actualizacion")

    fieldsets = (
        (
            "Identidad",
            {
                "fields": (
                    "nombre",
                    "slug",
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
