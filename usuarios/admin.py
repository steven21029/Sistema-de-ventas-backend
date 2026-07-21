from django.contrib import admin

from .models import CodigoVerificacionCorreo, PerfilUsuario


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = (
        "usuario",
        "empresa",
        "rol",
        "telefono",
        "numero_identidad",
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
        "numero_identidad",
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
                    "numero_identidad",
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


@admin.register(CodigoVerificacionCorreo)
class CodigoVerificacionCorreoAdmin(admin.ModelAdmin):
    list_display = (
        "usuario",
        "tipo",
        "usado",
        "intentos",
        "fecha_expiracion",
        "fecha_creacion",
        "fecha_uso",
    )
    list_filter = (
        "tipo",
        "usado",
        "fecha_creacion",
        "fecha_expiracion",
    )
    search_fields = (
        "usuario__username",
        "usuario__email",
    )
    readonly_fields = (
        "usuario",
        "codigo",
        "tipo",
        "usado",
        "intentos",
        "fecha_expiracion",
        "fecha_creacion",
        "fecha_uso",
    )
