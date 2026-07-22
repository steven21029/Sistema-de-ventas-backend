from django.contrib import admin

from .models import MensajeContacto


@admin.register(MensajeContacto)
class MensajeContactoAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "empresa",
        "telefono",
        "correo",
        "asunto",
        "estado",
        "fecha_creacion",
    )
    list_filter = ("empresa", "estado", "fecha_creacion")
    search_fields = (
        "nombre",
        "telefono",
        "correo",
        "asunto",
        "mensaje",
        "empresa__nombre",
    )
    readonly_fields = ("fecha_creacion", "fecha_actualizacion")
    ordering = ("-fecha_creacion", "-id")
