from django.contrib import admin

from .models import (
    Carrito,
    DetallePedido,
    DetallePedidoComponente,
    ItemCarrito,
    Pedido,
    Prefactura,
    TarifaEntrega,
)


class ItemCarritoInline(admin.TabularInline):
    model = ItemCarrito
    extra = 0
    autocomplete_fields = ("producto", "paquete")
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
    can_delete = False
    readonly_fields = (
        "producto",
        "paquete",
        "tipo_articulo",
        "codigo_articulo",
        "nombre_articulo",
        "codigo_interno",
        "codigo_barra",
        "nombre_producto",
        "precio_unitario",
        "cantidad",
        "promocion_codigo",
        "promocion_titulo",
        "porcentaje_descuento",
        "descuento_unitario",
        "precio_unitario_final",
        "descuento_total",
        "subtotal",
        "subtotal_final",
    )

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = (
        "numero",
        "usuario",
        "empresa",
        "tipo_entrega",
        "metodo_pago",
        "sucursal_pago",
        "estado_pago",
        "inventario_descontado",
        "subtotal",
        "impuesto",
        "total",
        "fecha_creacion",
    )
    list_filter = (
        "empresa",
        "tipo_entrega",
        "metodo_pago",
        "sucursal_pago",
        "estado_pago",
        "inventario_descontado",
        "moneda",
        "fecha_creacion",
    )
    search_fields = ("numero", "usuario__username", "usuario__email", "empresa__nombre")
    readonly_fields = (
        "empresa",
        "usuario",
        "carrito_origen",
        "numero",
        "tipo_entrega",
        "metodo_pago",
        "sucursal_pago",
        "nombre_recibe",
        "telefono_recibe",
        "direccion_entrega",
        "referencia_entrega",
        "departamento_entrega",
        "municipio_entrega",
        "subtotal",
        "descuento_total",
        "impuesto",
        "aplica_impuesto",
        "tasa_impuesto",
        "envio",
        "total",
        "moneda",
        "observaciones",
        "inventario_descontado",
        "fecha_creacion",
        "fecha_actualizacion",
    )
    inlines = [DetallePedidoInline]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


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
    list_display = (
        "carrito",
        "tipo_articulo",
        "articulo",
        "cantidad",
        "precio_unitario",
        "fecha_actualizacion",
    )
    list_filter = ("carrito__empresa",)
    search_fields = (
        "producto__nombre",
        "producto__codigo_interno",
        "producto__codigo_barra",
        "paquete__nombre",
        "paquete__codigo",
        "carrito__usuario__username",
    )
    autocomplete_fields = ("carrito", "producto", "paquete")
    readonly_fields = ("precio_unitario", "fecha_creacion", "fecha_actualizacion")


@admin.register(DetallePedido)
class DetallePedidoAdmin(admin.ModelAdmin):
    list_display = (
        "pedido",
        "tipo_articulo",
        "nombre_articulo",
        "codigo_articulo",
        "codigo_barra",
        "cantidad",
        "precio_unitario",
        "porcentaje_descuento",
        "descuento_total",
        "subtotal",
        "subtotal_final",
    )
    search_fields = (
        "pedido__numero",
        "nombre_producto",
        "nombre_articulo",
        "codigo_articulo",
        "codigo_interno",
        "codigo_barra",
        "promocion_codigo",
        "promocion_titulo",
    )
    readonly_fields = (
        "pedido",
        "producto",
        "paquete",
        "tipo_articulo",
        "codigo_articulo",
        "nombre_articulo",
        "codigo_interno",
        "codigo_barra",
        "nombre_producto",
        "precio_unitario",
        "cantidad",
        "promocion_codigo",
        "promocion_titulo",
        "porcentaje_descuento",
        "descuento_unitario",
        "precio_unitario_final",
        "descuento_total",
        "subtotal",
        "subtotal_final",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(DetallePedidoComponente)
class DetallePedidoComponenteAdmin(admin.ModelAdmin):
    list_display = (
        "detalle",
        "nombre_producto",
        "cantidad_por_unidad",
    )
    search_fields = (
        "detalle__pedido__numero",
        "nombre_producto",
        "codigo_interno",
        "codigo_barra",
    )
    readonly_fields = (
        "detalle",
        "producto",
        "codigo_interno",
        "codigo_barra",
        "nombre_producto",
        "cantidad_por_unidad",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Prefactura)
class PrefacturaAdmin(admin.ModelAdmin):
    list_display = (
        "numero",
        "pedido",
        "empresa",
        "cliente",
        "fecha_vencimiento",
        "intentos_correo",
        "correo_enviado_en",
        "fecha_creacion",
    )
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
        "fecha_vencimiento",
        "intentos_correo",
        "fecha_ultimo_intento_correo",
        "correo_enviado_en",
        "fecha_creacion",
        "fecha_actualizacion",
    )

    def empresa(self, obj):
        return obj.pedido.empresa

    def cliente(self, obj):
        return obj.pedido.usuario
