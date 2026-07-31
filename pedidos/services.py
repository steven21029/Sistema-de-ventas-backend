from decimal import Decimal, ROUND_HALF_UP

from promociones.services import mejores_descuentos_por_producto

from .models import ISV_RATE, MONEY_QUANTIZER


def redondear_monto(monto):
    return monto.quantize(MONEY_QUANTIZER, rounding=ROUND_HALF_UP)


def calcular_carrito(empresa, items):
    items = list(items)
    productos = [
        item["producto"]
        for item in items
        if item.get("producto") is not None
    ]
    descuentos = mejores_descuentos_por_producto(
        empresa,
        productos,
    )
    lineas = []
    subtotal = Decimal("0.00")
    descuento_total = Decimal("0.00")

    for item in items:
        producto = item.get("producto")
        paquete = item.get("paquete")
        cantidad = item["cantidad"]
        descuento = descuentos.get(producto.id) if producto else None
        porcentaje_descuento = descuento.porcentaje if descuento else 0
        precio_unitario = (
            producto.precio if producto else paquete.precio_paquete
        )
        descuento_unitario = redondear_monto(
            precio_unitario
            * Decimal(porcentaje_descuento)
            / Decimal("100")
        )
        precio_unitario_final = precio_unitario - descuento_unitario
        subtotal_linea = precio_unitario * cantidad
        descuento_linea = descuento_unitario * cantidad
        subtotal_final = precio_unitario_final * cantidad

        subtotal += subtotal_linea
        descuento_total += descuento_linea
        lineas.append(
            {
                "producto": producto,
                "paquete": paquete,
                "cantidad": cantidad,
                "precio_unitario": precio_unitario,
                "descuento": descuento,
                "porcentaje_descuento": porcentaje_descuento,
                "descuento_unitario": descuento_unitario,
                "precio_unitario_final": precio_unitario_final,
                "subtotal": subtotal_linea,
                "descuento_total": descuento_linea,
                "subtotal_final": subtotal_final,
            }
        )

    base_imponible = subtotal - descuento_total
    tasa_impuesto = ISV_RATE if empresa.cobra_impuesto else Decimal("0.0000")
    impuesto = redondear_monto(base_imponible * tasa_impuesto)
    total_sin_envio = redondear_monto(base_imponible + impuesto)

    return {
        "lineas": lineas,
        "subtotal": subtotal,
        "descuento_total": descuento_total,
        "base_imponible": base_imponible,
        "cobra_impuesto": empresa.cobra_impuesto,
        "tasa_impuesto": tasa_impuesto,
        "impuesto": impuesto,
        "total_sin_envio": total_sin_envio,
    }
