from django.db import migrations, models


def poblar_tipo_y_codigo_interno(apps, schema_editor):
    Producto = apps.get_model("catalogo", "Producto")

    for producto in Producto.objects.select_related("empresa").all().iterator():
        es_servicio = producto.empresa.modo_inventario == "sin_inventario"
        producto.tipo_item = "servicio" if es_servicio else "producto_fisico"
        prefijo = "SRV" if es_servicio else "PRD"
        producto.codigo_interno = f"{prefijo}-{producto.pk:012d}"
        producto.save(update_fields=["tipo_item", "codigo_interno"])


def limpiar_codigo_interno(apps, schema_editor):
    Producto = apps.get_model("catalogo", "Producto")
    Producto.objects.update(codigo_interno=None)


class Migration(migrations.Migration):
    dependencies = [
        ("empresas", "0011_empresa_modo_inventario"),
        ("catalogo", "0003_familia_imagen_familia_imagen_url_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="producto",
            name="tipo_item",
            field=models.CharField(
                choices=[
                    ("producto_fisico", "Producto fisico"),
                    ("servicio", "Servicio"),
                ],
                default="producto_fisico",
                help_text=(
                    "En empresas mixtas indica si se controla existencia o si es "
                    "un servicio."
                ),
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="producto",
            name="codigo_interno",
            field=models.CharField(
                editable=False,
                max_length=80,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="producto",
            name="codigo_barra",
            field=models.CharField(
                blank=True,
                max_length=80,
                null=True,
            ),
        ),
        migrations.RunPython(
            poblar_tipo_y_codigo_interno,
            limpiar_codigo_interno,
        ),
        migrations.AlterField(
            model_name="producto",
            name="codigo_interno",
            field=models.CharField(
                editable=False,
                max_length=80,
            ),
        ),
        migrations.AddConstraint(
            model_name="producto",
            constraint=models.UniqueConstraint(
                fields=("empresa", "codigo_interno"),
                name="producto_codigo_interno_unico_por_empresa",
            ),
        ),
    ]
