from django.contrib import admin

from .models import EventoWebhookPago, Pago


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = (
        "referencia",
        "pedido",
        "empresa",
        "usuario",
        "proveedor",
        "monto",
        "moneda",
        "estado",
        "fecha_creacion",
    )
    list_filter = ("empresa", "proveedor", "estado", "moneda", "fecha_creacion")
    search_fields = (
        "referencia",
        "pedido__numero",
        "identificador_externo",
        "usuario__username",
        "usuario__email",
    )
    readonly_fields = (
        "pedido",
        "empresa",
        "usuario",
        "referencia",
        "proveedor",
        "identificador_externo",
        "monto",
        "moneda",
        "estado",
        "url_pago",
        "codigo_respuesta",
        "fecha_confirmacion",
        "fecha_creacion",
        "fecha_actualizacion",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(EventoWebhookPago)
class EventoWebhookPagoAdmin(admin.ModelAdmin):
    list_display = (
        "evento_id",
        "proveedor",
        "pago",
        "estado_recibido",
        "procesado",
        "fecha_creacion",
    )
    list_filter = ("proveedor", "estado_recibido", "procesado", "fecha_creacion")
    search_fields = ("evento_id", "referencia_pago", "pago__referencia")
    readonly_fields = (
        "pago",
        "proveedor",
        "evento_id",
        "referencia_pago",
        "estado_recibido",
        "hash_payload",
        "procesado",
        "mensaje",
        "fecha_creacion",
        "fecha_actualizacion",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
