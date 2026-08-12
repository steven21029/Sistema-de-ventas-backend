from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("empresas", "0017_sucursalempresa_ciudad"),
    ]

    operations = [
        migrations.AddField(
            model_name="empresa",
            name="pago_en_linea_activo",
            field=models.BooleanField(
                default=False,
                help_text="Si esta activo, el checkout puede ofrecer pago en linea.",
            ),
        ),
        migrations.AddField(
            model_name="empresa",
            name="pago_en_linea_proveedor",
            field=models.CharField(
                blank=True,
                choices=[
                    ("simulado", "Simulado"),
                    ("paypal", "PayPal"),
                    ("stripe", "Stripe"),
                    ("bac", "BAC Credomatic"),
                    ("otro", "Otro proveedor"),
                ],
                default="",
                help_text="Proveedor que procesara los cobros en linea de esta empresa.",
                max_length=50,
            ),
        ),
        migrations.AddField(
            model_name="empresa",
            name="pago_en_linea_modo",
            field=models.CharField(
                choices=[
                    ("pruebas", "Pruebas"),
                    ("produccion", "Produccion"),
                ],
                default="pruebas",
                help_text="Modo de operacion del proveedor de pago en linea.",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="empresa",
            name="pago_en_linea_credencial_publica",
            field=models.CharField(
                blank=True,
                default="",
                help_text=(
                    "Clave publica, merchant ID o identificador visible del proveedor."
                ),
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="empresa",
            name="pago_en_linea_credencial_secreta",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Clave secreta o token privado del proveedor. No se expone por API.",
                max_length=500,
            ),
        ),
        migrations.AddField(
            model_name="empresa",
            name="pago_en_linea_webhook_secreto",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Secreto usado para validar webhooks del proveedor.",
                max_length=500,
            ),
        ),
    ]
