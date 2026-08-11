from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("empresas", "0016_empresa_facebook_url_empresa_instagram_url_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="sucursalempresa",
            name="ciudad",
            field=models.CharField(blank=True, db_index=True, max_length=120),
        ),
    ]
