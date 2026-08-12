import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("empresas", "0019_ubicaciones_municipios"),
        ("usuarios", "0007_alter_perfilusuario_telefono"),
    ]

    operations = [
        migrations.AddField(
            model_name="perfilusuario",
            name="municipio",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="perfiles_usuario",
                to="empresas.municipio",
            ),
        ),
    ]
