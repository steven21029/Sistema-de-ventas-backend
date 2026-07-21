from django.contrib import admin

from .models import Carrito, DetallePedido, ItemCarrito, Pedido, Prefactura, TarifaEntrega


class ItemCarritoInline(admin.TabularInline):
    model = ItemCarrito
    extra = 0
    autocomplete_fields = ("producto",)
    readonly_fields = ("precio_unitario", "fecha_creacion", "fecha_actualizacion")


@admin.register(Carrito)
class CarritoAdmin(admin.ModelAdmin):
    list_display = ("usuario", "empresa", "activo", "fecha_actualizacion")
    list_filter = ("empresa", "activo")
    search_fields = ("usuario__username", "usuario__email", "empresa__nombre")
    autocomplete_fields = ("empresa", "usuario")
    readonly_fields = ("fecha_creacion", "fecha_actualizacion")
    inlines = [ItemCarritoInline]


class DetallePedidoInline(admin.TabularInline):
    model = DetallePedido
    extra = 0
    autocomplete_fields = ("producto",)
    readonly_fields = ("codigo_barra", "nombre_producto", "subtotal")


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = (
        "numero",
        "usuario",
        "empresa",
        "tipo_entrega",
        "estado_pago",
        "inventario_descontado",
        "subtotal",
        "total",
        "fecha_creacion",
    )
    list_filter = (
        "empresa",
        "tipo_entrega",
        "estado_pago",
        "inventario_descontado",
        "moneda",
        "fecha_creacion",
    )
    search_fields = ("numero", "usuario__username", "usuario__email", "empresa__nombre")
    autocomplete_fields = ("empresa", "usuario", "carrito_origen")
    readonly_fields = (
        "numero",
        "impuesto",
        "envio",
        "total",
        "inventario_descontado",
        "fecha_creacion",
        "fecha_actualizacion",
    )
    inlines = [DetallePedidoInline]


@admin.register(TarifaEntrega)
class TarifaEntregaAdmin(admin.ModelAdmin):
    list_display = (
        "empresa",
        "tipo_entrega",
        "monto",
        "activa",
        "fecha_actualizacion",
    )
    list_filter = ("empresa", "tipo_entrega", "activa")
    search_fields = ("empresa__nombre",)
    autocomplete_fields = ("empresa",)
    readonly_fields = ("fecha_creacion", "fecha_actualizacion")


@admin.register(ItemCarrito)
class ItemCarritoAdmin(admin.ModelAdmin):
    list_display = ("carrito", "producto", "cantidad", "precio_unitario", "fecha_actualizacion")
    list_filter = ("carrito__empresa",)
    search_fields = ("producto__nombre", "producto__codigo_barra", "carrito__usuario__username")
    autocomplete_fields = ("carrito", "producto")
    readonly_fields = ("precio_unitario", "fecha_creacion", "fecha_actualizacion")


@admin.register(DetallePedido)
class DetallePedidoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "nombre_producto", "codigo_barra", "cantidad", "precio_unitario", "subtotal")
    search_fields = ("pedido__numero", "nombre_producto", "codigo_barra")
    autocomplete_fields = ("pedido", "producto")
    readonly_fields = ("codigo_barra", "nombre_producto", "subtotal")


@admin.register(Prefactura)
class PrefacturaAdmin(admin.ModelAdmin):
    list_display = ("numero", "pedido", "empresa", "cliente", "fecha_creacion")
    search_fields = (
        "numero",
        "pedido__numero",
        "pedido__usuario__username",
        "pedido__usuario__email",
        "pedido__empresa__nombre",
    )
    list_filter = ("pedido__empresa", "fecha_creacion")
    autocomplete_fields = ("pedido",)
    readonly_fields = (
        "numero",
        "leyenda",
        "fecha_creacion",
        "fecha_actualizacion",
    )

    def empresa(self, obj):
        return obj.pedido.empresa

    def cliente(self, obj):
        return obj.pedido.usuario
