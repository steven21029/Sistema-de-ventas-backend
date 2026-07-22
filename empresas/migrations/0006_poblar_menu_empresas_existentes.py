from django.db import migrations


MENU_PREDETERMINADO = [
    ("inicio", "Inicio", "/", 1),
    ("examenes", "Examenes", "/examenes", 2),
    ("perfiles", "Perfiles", "/perfiles", 3),
    ("servicios", "Servicios", "/servicios", 4),
    ("promociones", "Promociones", "/promociones", 5),
    ("sucursales", "Sucursales", "/sucursales", 6),
    ("contacto", "Contacto", "/contacto", 7),
]


def poblar_menu_empresas(apps, schema_editor):
    Empresa = apps.get_model("empresas", "Empresa")
    ItemMenuEmpresa = apps.get_model("empresas", "ItemMenuEmpresa")

    for empresa in Empresa.objects.all():
        for clave, texto, ruta, orden in MENU_PREDETERMINADO:
            ItemMenuEmpresa.objects.get_or_create(
                empresa=empresa,
                clave=clave,
                defaults={
                    "texto": texto,
                    "ruta": ruta,
                    "orden": orden,
                    "activo": True,
                    "abre_en_nueva_pestana": False,
                },
            )


class Migration(migrations.Migration):

    dependencies = [
        ("empresas", "0005_itemmenuempresa"),
    ]

    operations = [
        migrations.RunPython(poblar_menu_empresas, migrations.RunPython.noop),
    ]
