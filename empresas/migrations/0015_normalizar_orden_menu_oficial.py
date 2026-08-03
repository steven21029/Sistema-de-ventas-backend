from django.db import migrations


def normalizar_orden_menu(apps, schema_editor):
    Empresa = apps.get_model("empresas", "Empresa")
    ItemMenuEmpresa = apps.get_model("empresas", "ItemMenuEmpresa")

    for empresa in Empresa.objects.all().iterator():
        items = list(
            ItemMenuEmpresa.objects.filter(empresa=empresa).order_by("orden", "id")
        )
        ordenes_reservados = {item.orden for item in items if item.orden > 0}
        ordenes_usados = set()

        for item in items:
            if item.orden > 0 and item.orden not in ordenes_usados:
                ordenes_usados.add(item.orden)
                continue

            nuevo_orden = 1
            while (
                nuevo_orden in ordenes_reservados
                or nuevo_orden in ordenes_usados
            ):
                nuevo_orden += 1

            ItemMenuEmpresa.objects.filter(pk=item.pk).update(orden=nuevo_orden)
            ordenes_usados.add(nuevo_orden)


class Migration(migrations.Migration):

    dependencies = [
        ("empresas", "0014_sobrenosotrosempresa_alter_itemmenuempresa_clave_and_more"),
    ]

    operations = [
        migrations.RunPython(
            normalizar_orden_menu,
            migrations.RunPython.noop,
        ),
    ]
