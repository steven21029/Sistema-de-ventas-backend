import unicodedata

import django.db.models.deletion
from django.db import migrations, models


PRIORIDAD_MUNICIPIOS = {
    "0801": 1,  # Distrito Central
    "0301": 2,  # Comayagua
    "0501": 3,  # San Pedro Sula
    "0601": 4,  # Choluteca
}


ALIAS_MUNICIPIOS_SUCURSALES = {
    "tegucigalpa": "0801",
    "tegucigalpa mdc": "0801",
    "teg": "0801",
    "comayaguela": "0801",
    "comayaguela mdc": "0801",
    "distrito central": "0801",
    "comayagua": "0301",
    "san pedro sula": "0501",
    "sps": "0501",
    "choloma": "0502",
    "cholona": "0502",
    "lopez arellano": "0502",
    "la lima": "0512",
    "calpules": "0512",
    "choluteca": "0601",
    "san marcos de colon": "0615",
    "danli": "0703",
    "el paraiso": "0704",
    "zamorano": "0817",
    "el zamorano": "0817",
    "san antonio de oriente": "0817",
    "san lorenzo": "1709",
}


def normalizar_nombre(value):
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(caracter for caracter in value if not unicodedata.combining(caracter))
    return " ".join(value.casefold().strip().split())


def obtener_ordenes_municipios(municipios):
    prioridad = list(PRIORIDAD_MUNICIPIOS)
    codigos = prioridad + [codigo for codigo, _nombre in municipios if codigo not in PRIORIDAD_MUNICIPIOS]
    return {codigo: indice for indice, codigo in enumerate(codigos, start=1)}


def poblar_catalogo_y_relacionar_sucursales(apps, schema_editor):
    from empresas.datos_honduras import DEPARTAMENTOS_HONDURAS, MUNICIPIOS_HONDURAS

    Departamento = apps.get_model("empresas", "Departamento")
    Municipio = apps.get_model("empresas", "Municipio")
    SucursalEmpresa = apps.get_model("empresas", "SucursalEmpresa")
    db_alias = schema_editor.connection.alias

    departamentos = {}
    for codigo, nombre in DEPARTAMENTOS_HONDURAS:
        departamento, _created = Departamento.objects.using(db_alias).update_or_create(
            codigo=codigo,
            defaults={
                "nombre": nombre,
                "orden": int(codigo),
                "activo": True,
            },
        )
        departamentos[codigo] = departamento

    ordenes_municipios = obtener_ordenes_municipios(MUNICIPIOS_HONDURAS)
    for codigo, nombre in MUNICIPIOS_HONDURAS:
        Municipio.objects.using(db_alias).update_or_create(
            codigo=codigo,
            defaults={
                "departamento": departamentos[codigo[:2]],
                "nombre": nombre,
                "nombre_normalizado": normalizar_nombre(nombre),
                "orden": ordenes_municipios[codigo],
                "activo": True,
            },
        )

    municipios_por_codigo = {
        municipio.codigo: municipio
        for municipio in Municipio.objects.using(db_alias).select_related("departamento")
    }
    municipios_por_nombre = {}
    conteo_nombres = {}
    for municipio in municipios_por_codigo.values():
        nombre_normalizado = normalizar_nombre(municipio.nombre)
        conteo_nombres[nombre_normalizado] = conteo_nombres.get(nombre_normalizado, 0) + 1
        municipios_por_nombre[nombre_normalizado] = municipio

    for sucursal in SucursalEmpresa.objects.using(db_alias).all():
        if sucursal.estado == "activa" and not sucursal.activa:
            sucursal.estado = "inactiva"
        elif not sucursal.estado:
            sucursal.estado = "activa" if sucursal.activa else "inactiva"

        ciudad_normalizada = normalizar_nombre(sucursal.ciudad)
        codigo = ALIAS_MUNICIPIOS_SUCURSALES.get(ciudad_normalizada)
        municipio = municipios_por_codigo.get(codigo) if codigo else None
        if municipio is None and conteo_nombres.get(ciudad_normalizada) == 1:
            municipio = municipios_por_nombre[ciudad_normalizada]

        campos = ["estado"]
        if municipio:
            sucursal.municipio_id = municipio.pk
            sucursal.ciudad = municipio.nombre
            campos.extend(["municipio", "ciudad"])
        sucursal.save(update_fields=campos)


class Migration(migrations.Migration):

    dependencies = [
        ("empresas", "0018_empresa_pago_en_linea"),
    ]

    operations = [
        migrations.CreateModel(
            name="Departamento",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("codigo", models.CharField(max_length=2, unique=True)),
                ("nombre", models.CharField(max_length=120)),
                ("orden", models.PositiveIntegerField(default=0)),
                ("activo", models.BooleanField(default=True)),
                ("fecha_creacion", models.DateTimeField(auto_now_add=True)),
                ("fecha_actualizacion", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "departamento",
                "verbose_name_plural": "departamentos",
                "ordering": ["orden", "nombre"],
            },
        ),
        migrations.CreateModel(
            name="Municipio",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("codigo", models.CharField(max_length=4, unique=True)),
                ("nombre", models.CharField(max_length=120)),
                ("nombre_normalizado", models.CharField(editable=False, max_length=120)),
                ("orden", models.PositiveIntegerField(default=0)),
                ("activo", models.BooleanField(default=True)),
                ("fecha_creacion", models.DateTimeField(auto_now_add=True)),
                ("fecha_actualizacion", models.DateTimeField(auto_now=True)),
                ("departamento", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="municipios", to="empresas.departamento")),
            ],
            options={
                "verbose_name": "municipio",
                "verbose_name_plural": "municipios",
                "ordering": ["departamento__orden", "orden", "nombre"],
            },
        ),
        migrations.AddField(
            model_name="sucursalempresa",
            name="estado",
            field=models.CharField(
                choices=[
                    ("activa", "Activa"),
                    ("temporalmente_cerrada", "Temporalmente cerrada"),
                    ("inactiva", "Inactiva"),
                ],
                db_index=True,
                default="activa",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="sucursalempresa",
            name="municipio",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sucursales", to="empresas.municipio"),
        ),
        migrations.AddIndex(
            model_name="departamento",
            index=models.Index(fields=["activo", "orden"], name="empresas_de_activo_a227ab_idx"),
        ),
        migrations.AddIndex(
            model_name="municipio",
            index=models.Index(fields=["departamento", "activo", "orden"], name="empresas_mu_departa_97a4c6_idx"),
        ),
        migrations.AddIndex(
            model_name="municipio",
            index=models.Index(fields=["departamento", "nombre_normalizado"], name="empresas_mu_departa_bffba7_idx"),
        ),
        migrations.AddConstraint(
            model_name="municipio",
            constraint=models.UniqueConstraint(fields=("departamento", "nombre_normalizado"), name="municipio_nombre_normalizado_unico_por_departamento"),
        ),
        migrations.AddIndex(
            model_name="sucursalempresa",
            index=models.Index(fields=["empresa", "estado", "orden"], name="empresas_su_empresa_b597c8_idx"),
        ),
        migrations.AddIndex(
            model_name="sucursalempresa",
            index=models.Index(fields=["municipio", "estado"], name="empresas_su_municip_ff8c68_idx"),
        ),
        migrations.RunPython(
            poblar_catalogo_y_relacionar_sucursales,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
