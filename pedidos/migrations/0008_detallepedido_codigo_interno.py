from django.db import migrations, models


def poblar_codigo_interno(apps, schema_editor):
    DetallePedido = apps.get_model("pedidos", "DetallePedido")

    for detalle in DetallePedido.objects.select_related("producto").all().iterator():
        detalle.codigo_interno = detalle.producto.codigo_interno
        detalle.save(update_fields=["codigo_interno"])


def limpiar_codigo_interno(apps, schema_editor):
    DetallePedido = apps.get_model("pedidos", "DetallePedido")
    DetallePedido.objects.update(codigo_interno=None)


class Migration(migrations.Migration):
    dependencies = [
        ("catalogo", "0004_producto_tipo_item_y_codigo_interno"),
        (
            "pedidos",
            "0007_pedido_departamento_entrega_pedido_direccion_entrega_and_more",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="detallepedido",
            name="codigo_interno",
            field=models.CharField(
                editable=False,
                max_length=80,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="detallepedido",
            name="codigo_barra",
            field=models.CharField(
                blank=True,
                editable=False,
                max_length=80,
                null=True,
            ),
        ),
        migrations.RunPython(
            poblar_codigo_interno,
            limpiar_codigo_interno,
        ),
        migrations.AlterField(
            model_name="detallepedido",
            name="codigo_interno",
            field=models.CharField(
                editable=False,
                max_length=80,
            ),
        ),
    ]
