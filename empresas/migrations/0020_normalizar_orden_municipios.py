from django.db import migrations


PRIORIDAD_MUNICIPIOS = [
    "0801",  # Distrito Central
    "0301",  # Comayagua
    "0501",  # San Pedro Sula
    "0601",  # Choluteca
]


def normalizar_orden_municipios(apps, schema_editor):
    from empresas.datos_honduras import MUNICIPIOS_HONDURAS

    Municipio = apps.get_model("empresas", "Municipio")
    db_alias = schema_editor.connection.alias

    codigos = PRIORIDAD_MUNICIPIOS + [
        codigo
        for codigo, _nombre in MUNICIPIOS_HONDURAS
        if codigo not in PRIORIDAD_MUNICIPIOS
    ]
    ordenes = {codigo: indice for indice, codigo in enumerate(codigos, start=1)}

    municipios = list(Municipio.objects.using(db_alias).filter(codigo__in=ordenes))
    for municipio in municipios:
        municipio.orden = ordenes[municipio.codigo]

    Municipio.objects.using(db_alias).bulk_update(municipios, ["orden"])


class Migration(migrations.Migration):

    dependencies = [
        ("empresas", "0019_ubicaciones_municipios"),
    ]

    operations = [
        migrations.RunPython(
            normalizar_orden_municipios,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
