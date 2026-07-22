from django.db import migrations
from django.utils.text import slugify


SUBDOMINIOS_RESERVADOS = {"admin", "api", "app", "media", "static", "www"}


def poblar_subdominios(apps, schema_editor):
    Empresa = apps.get_model("empresas", "Empresa")
    usados = {
        subdominio.lower()
        for subdominio in Empresa.objects.exclude(subdominio__isnull=True)
        .exclude(subdominio="")
        .values_list("subdominio", flat=True)
    }

    for empresa in Empresa.objects.filter(subdominio__isnull=True):
        base = slugify(empresa.slug or empresa.nombre).lower()[:63].strip("-")
        if not base or base in SUBDOMINIOS_RESERVADOS:
            base = f"empresa-{empresa.pk}"

        subdominio = base
        contador = 2
        while subdominio in usados:
            sufijo = f"-{contador}"
            subdominio = f"{base[: 63 - len(sufijo)]}{sufijo}"
            contador += 1

        usados.add(subdominio)
        empresa.subdominio = subdominio
        empresa.save(update_fields=["subdominio"])


class Migration(migrations.Migration):

    dependencies = [
        ("empresas", "0003_empresa_dominio_personalizado_empresa_subdominio"),
    ]

    operations = [
        migrations.RunPython(poblar_subdominios, migrations.RunPython.noop),
    ]
