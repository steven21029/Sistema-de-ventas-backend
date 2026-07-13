from django.contrib import admin

from .models import PerfilUsuario


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = (
        "usuario",
        "empresa",
        "rol",
        "telefono",
        "correo_verificado",
        "activo",
    )
    list_filter = (
        "rol",
        "empresa",
        "correo_verificado",
        "puede_crear_usuarios",
        "activo",
    )
    search_fields = (
        "usuario__username",
        "usuario__email",
        "usuario__first_name",
        "usuario__last_name",
        "telefono",
    )
    autocomplete_fields = ("empresa",)
    readonly_fields = ("fecha_creacion", "fecha_actualizacion")

    fieldsets = (
        (
            "Usuario",
            {
                "fields": (
                    "usuario",
                    "empresa",
                    "rol",
                )
            },
        ),
        (
            "Contacto y verificacion",
            {
                "fields": (
                    "telefono",
                    "correo_verificado",
                )
            },
        ),
        (
            "Permisos iniciales",
            {
                "fields": (
                    "puede_crear_usuarios",
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
