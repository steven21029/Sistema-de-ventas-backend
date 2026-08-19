from django.contrib import admin

from .models import CodigoVerificacionCorreo, PerfilUsuario


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = (
        "usuario",
        "empresa",
        "municipio",
        "rol",
        "telefono",
        "numero_identidad",
        "correo_verificado",
        "acepta_promociones",
        "activo",
    )
    list_filter = (
        "rol",
        "empresa",
        "municipio",
        "municipio__departamento",
        "correo_verificado",
        "acepta_promociones",
        "puede_crear_usuarios",
        "activo",
    )
    search_fields = (
        "usuario__username",
        "usuario__email",
        "usuario__first_name",
        "usuario__last_name",
        "municipio__nombre",
        "municipio__departamento__nombre",
        "telefono",
        "numero_identidad",
    )
    autocomplete_fields = ("empresa", "municipio")
    readonly_fields = (
        "acepta_terminos",
        "acepta_privacidad",
        "fecha_aceptacion_terminos_privacidad",
        "version_terminos_aceptada",
        "version_privacidad_aceptada",
        "acepta_promociones",
        "fecha_aceptacion_promociones",
        "fecha_retiro_promociones",
        "fecha_creacion",
        "fecha_actualizacion",
    )

    fieldsets = (
        (
            "Usuario",
            {
                "fields": (
                    "usuario",
                    "empresa",
                    "municipio",
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
            "Consentimientos",
            {
                "fields": (
                    "acepta_terminos",
                    "acepta_privacidad",
                    "fecha_aceptacion_terminos_privacidad",
                    "version_terminos_aceptada",
                    "version_privacidad_aceptada",
                    "acepta_promociones",
                    "fecha_aceptacion_promociones",
                    "fecha_retiro_promociones",
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
