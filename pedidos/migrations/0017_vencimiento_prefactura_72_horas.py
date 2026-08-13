from datetime import timedelta

from django.db import migrations, models
from django.utils import timezone

import pedidos.models


def actualizar_vigencia_prefacturas(apps, schema_editor):
    Pedido = apps.get_model("pedidos", "Pedido")
    Prefactura = apps.get_model("pedidos", "Prefactura")
    Pago = apps.get_model("pagos", "Pago")
    ahora = timezone.now()

    prefacturas = Prefactura.objects.filter(
        pedido__estado_pago="pendiente",
        pedido__metodo_pago="sucursal",
    ).only("id", "pedido_id", "fecha_creacion", "fecha_vencimiento")
    for prefactura in prefacturas.iterator():
        fecha_vencimiento = prefactura.fecha_creacion + timedelta(hours=72)
        Prefactura.objects.filter(pk=prefactura.pk).update(
            fecha_vencimiento=fecha_vencimiento,
        )
        if fecha_vencimiento > ahora:
            continue
        if Pago.objects.filter(
            pedido_id=prefactura.pedido_id,
            estado="aprobado",
        ).exists():
            continue

        Pago.objects.filter(
            pedido_id=prefactura.pedido_id,
            estado="pendiente",
        ).update(
            estado="rechazado",
            codigo_respuesta="PREFACTURA_VENCIDA",
            fecha_confirmacion=ahora,
            fecha_actualizacion=ahora,
        )
        Pedido.objects.filter(
            pk=prefactura.pedido_id,
            estado_pago="pendiente",
        ).update(
            estado_pago="rechazado",
            fecha_actualizacion=ahora,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("pagos", "0003_alter_pago_estado"),
        ("pedidos", "0016_pedido_municipio_entrega_catalogo"),
    ]

    operations = [
        migrations.AlterField(
            model_name="pedido",
            name="estado_pago",
            field=models.CharField(
                choices=[
                    ("pendiente", "Pendiente"),
                    ("pagado", "Pagado"),
                    ("rechazado", "Rechazado"),
                    ("cancelado", "Cancelado"),
                ],
                default="pendiente",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="prefactura",
            name="fecha_vencimiento",
            field=models.DateTimeField(
                db_index=True,
                default=pedidos.models.fecha_vencimiento_prefactura,
            ),
        ),
        migrations.RunPython(
            actualizar_vigencia_prefacturas,
            migrations.RunPython.noop,
        ),
    ]
