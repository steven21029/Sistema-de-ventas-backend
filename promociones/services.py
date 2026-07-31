from django.db.models import Prefetch, Q
from django.utils import timezone

from .models import DescuentoProducto, DescuentoPromocional


def mejores_descuentos_por_producto(empresa, productos, ahora=None):
    productos = list(productos)
    productos_ids = {producto.id for producto in productos}
    if not productos_ids:
        return {}

    ahora = ahora or timezone.now()
    items_prefetch = Prefetch(
        "items_productos",
        queryset=DescuentoProducto.objects.only(
            "id",
            "descuento_id",
            "producto_id",
        ),
    )
    descuentos = (
        DescuentoPromocional.objects.filter(
            empresa=empresa,
            activo=True,
        )
        .filter(
            Q(fecha_inicio__isnull=True) | Q(fecha_inicio__lte=ahora),
            Q(fecha_fin__isnull=True) | Q(fecha_fin__gte=ahora),
        )
        .prefetch_related(items_prefetch)
    )

    ganadores = {}
    claves_ganadoras = {}

    for descuento in descuentos:
        seleccionados = {
            item.producto_id for item in descuento.items_productos.all()
        }
        if descuento.alcance == DescuentoPromocional.Alcance.TODOS:
            if seleccionados:
                continue
            aplicables = productos_ids
        elif descuento.alcance == DescuentoPromocional.Alcance.INDIVIDUAL:
            if len(seleccionados) != 1:
                continue
            aplicables = productos_ids & seleccionados
        else:
            if len(seleccionados) < 2:
                continue
            aplicables = productos_ids & seleccionados

        clave = (
            descuento.porcentaje,
            descuento.prioridad_alcance,
            -descuento.id,
        )
        for producto_id in aplicables:
            if clave > claves_ganadoras.get(producto_id, (0, 0, 0)):
                claves_ganadoras[producto_id] = clave
                ganadores[producto_id] = descuento

    return ganadores
