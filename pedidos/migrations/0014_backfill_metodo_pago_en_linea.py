from django.db import migrations


def backfill_metodo_pago_en_linea(apps, schema_editor):
    Pedido = apps.get_model("pedidos", "Pedido")
    Pago = apps.get_model("pagos", "Pago")
    pedidos_con_pago = Pago.objects.values_list("pedido_id", flat=True).distinct()
    Pedido.objects.filter(
        pk__in=pedidos_con_pago,
        metodo_pago="pendiente",
    ).update(metodo_pago="en_linea")


class Migration(migrations.Migration):
    dependencies = [
        ("pagos", "0002_pago_metodo_pago_pagos_pago_empresa_32ac8c_idx"),
        ("pedidos", "0013_pedido_metodo_pago_pedido_sucursal_pago_and_more"),
    ]

    operations = [
        migrations.RunPython(
            backfill_metodo_pago_en_linea,
            migrations.RunPython.noop,
        ),
    ]
