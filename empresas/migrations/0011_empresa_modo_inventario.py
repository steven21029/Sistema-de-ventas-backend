from django.db import migrations, models


def configurar_analiza_sin_inventario(apps, schema_editor):
    Empresa = apps.get_model("empresas", "Empresa")
    Empresa.objects.filter(slug__iexact="Analiza").update(
        modo_inventario="sin_inventario"
    )


def revertir_analiza_a_inventariado(apps, schema_editor):
    Empresa = apps.get_model("empresas", "Empresa")
    Empresa.objects.filter(slug__iexact="Analiza").update(
        modo_inventario="inventariado"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("empresas", "0010_empresa_imagen_sucursales_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="empresa",
            name="modo_inventario",
            field=models.CharField(
                choices=[
                    ("inventariado", "Con inventario"),
                    ("sin_inventario", "Sin inventario (servicios)"),
                    ("mixto", "Mixto"),
                ],
                default="inventariado",
                help_text=(
                    "Define si la empresa vende productos fisicos, servicios o ambos."
                ),
                max_length=20,
            ),
        ),
        migrations.RunPython(
            configurar_analiza_sin_inventario,
            revertir_analiza_a_inventariado,
        ),
    ]
