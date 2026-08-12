import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("empresas", "0019_ubicaciones_municipios"),
        ("pedidos", "0015_pedido_cancelado_por_pedido_fecha_cancelacion_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="pedido",
            name="municipio_entrega_catalogo",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="pedidos_entrega",
                to="empresas.municipio",
            ),
        ),
    ]
