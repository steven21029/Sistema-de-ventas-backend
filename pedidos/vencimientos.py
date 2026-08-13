from dataclasses import dataclass

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from pagos.models import Pago

from .models import Pedido, Prefactura


MENSAJE_VIGENCIA_PREFACTURA = (
    "Esta prefactura estara disponible durante "
    f"{settings.PREFACTURA_VIGENCIA_HORAS} horas a partir de su emision. "
    "Dentro de ese plazo se respetaran los precios y el total indicados. Si el "
    "pago no es confirmado en la sucursal antes del vencimiento, el pedido sera "
    "rechazado automaticamente y debera realizar una nueva compra."
)


@dataclass(frozen=True)
class ResultadoVencimiento:
    vencida: bool = False
    pedido_actualizado: bool = False
    pagos_actualizados: int = 0


def vencer_prefactura_sucursal(pedido_id, ahora=None):
    ahora = ahora or timezone.now()
    with transaction.atomic():
        pedido = (
            Pedido.objects.select_for_update()
            .filter(pk=pedido_id)
            .first()
        )
        if not pedido:
            return ResultadoVencimiento()

        prefactura = (
            Prefactura.objects.select_for_update()
            .filter(pedido_id=pedido_id)
            .first()
        )
        if (
            not prefactura
            or pedido.metodo_pago != Pedido.MetodoPago.SUCURSAL
            or prefactura.fecha_vencimiento > ahora
        ):
            return ResultadoVencimiento()

        if pedido.estado_pago == Pedido.EstadoPago.RECHAZADO:
            return ResultadoVencimiento(vencida=True)
        if pedido.estado_pago != Pedido.EstadoPago.PENDIENTE:
            return ResultadoVencimiento()

        pagos = list(
            Pago.objects.select_for_update()
            .filter(pedido_id=pedido_id)
            .order_by("id")
        )
        if any(pago.estado == Pago.Estado.APROBADO for pago in pagos):
            return ResultadoVencimiento()

        pagos_actualizados = 0
        for pago in pagos:
            if pago.estado != Pago.Estado.PENDIENTE:
                continue
            if pago.rechazar_por_vencimiento_prefactura(ahora):
                pagos_actualizados += 1

        pedido_actualizado = pedido.rechazar_por_vencimiento_prefactura()
        return ResultadoVencimiento(
            vencida=True,
            pedido_actualizado=pedido_actualizado,
            pagos_actualizados=pagos_actualizados,
        )


def vencer_prefacturas_sucursal(
    *,
    ahora=None,
    empresa_ids=None,
    usuario_id=None,
    pedido_ids=None,
):
    ahora = ahora or timezone.now()
    candidatas = Prefactura.objects.filter(
        fecha_vencimiento__lte=ahora,
        pedido__estado_pago=Pedido.EstadoPago.PENDIENTE,
        pedido__metodo_pago=Pedido.MetodoPago.SUCURSAL,
    )
    if empresa_ids is not None:
        candidatas = candidatas.filter(pedido__empresa_id__in=list(empresa_ids))
    if usuario_id is not None:
        candidatas = candidatas.filter(pedido__usuario_id=usuario_id)
    if pedido_ids is not None:
        candidatas = candidatas.filter(pedido_id__in=list(pedido_ids))

    resultado = {
        "prefacturas_vencidas": 0,
        "pedidos_rechazados": 0,
        "pagos_rechazados": 0,
    }
    for pedido_id in candidatas.order_by("pedido_id").values_list(
        "pedido_id",
        flat=True,
    ):
        vencimiento = vencer_prefactura_sucursal(pedido_id, ahora=ahora)
        if not vencimiento.vencida:
            continue
        resultado["prefacturas_vencidas"] += 1
        resultado["pedidos_rechazados"] += int(
            vencimiento.pedido_actualizado
        )
        resultado["pagos_rechazados"] += vencimiento.pagos_actualizados
    return resultado


def confirmar_pago_sucursal_transaccional(referencia):
    pago_consultado = Pago.objects.only("pedido_id").get(referencia=referencia)
    with transaction.atomic():
        vencimiento = vencer_prefactura_sucursal(
            pago_consultado.pedido_id,
            ahora=timezone.now(),
        )
        if vencimiento.vencida:
            pago = Pago.objects.select_related("pedido").get(referencia=referencia)
            return pago, False, True

        pago, cambio = Pago.procesar_resultado(
            referencia=referencia,
            proveedor="sucursal",
            estado=Pago.Estado.APROBADO,
            identificador_externo=f"SUC-{referencia}",
            codigo_respuesta="CONFIRMADO_SUCURSAL",
        )
        return pago, cambio, False
