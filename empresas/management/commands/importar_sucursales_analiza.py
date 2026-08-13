import unicodedata

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from empresas.models import Empresa, Municipio, SucursalEmpresa


HORARIO_630_500 = (
    "Lunes a viernes: 6:30 a.m. - 5:00 p.m.\n"
    "Sábado: 6:30 a.m. - 1:00 p.m.\n"
    "Domingo: Cerrado"
)
HORARIO_630_400 = (
    "Lunes a viernes: 6:30 a.m. - 4:00 p.m.\n"
    "Sábado: 6:30 a.m. - 1:00 p.m.\n"
    "Domingo: Cerrado"
)
HORARIO_600_500 = (
    "Lunes a viernes: 6:00 a.m. - 5:00 p.m.\n"
    "Sábado: 6:00 a.m. - 1:00 p.m.\n"
    "Domingo: Cerrado"
)
HORARIO_600_500_DOMINGO = (
    "Lunes a viernes: 6:00 a.m. - 5:00 p.m.\n"
    "Sábado: 6:00 a.m. - 1:00 p.m.\n"
    "Domingo: 7:00 a.m. - 12:00 p.m."
)
HORARIO_600_600 = (
    "Lunes a viernes: 6:00 a.m. - 6:00 p.m.\n"
    "Sábado: 6:00 a.m. - 3:00 p.m.\n"
    "Domingo: Cerrado"
)
HORARIO_600_600_DOMINGO_12 = (
    "Lunes a viernes: 6:00 a.m. - 6:00 p.m.\n"
    "Sábado: 6:00 a.m. - 3:00 p.m.\n"
    "Domingo: 7:00 a.m. - 12:00 p.m."
)
HORARIO_600_600_DOMINGO_1 = (
    "Lunes a viernes: 6:00 a.m. - 6:00 p.m.\n"
    "Sábado: 6:00 a.m. - 3:00 p.m.\n"
    "Domingo: 7:00 a.m. - 1:00 p.m."
)
HORARIO_630_600 = (
    "Lunes a viernes: 6:30 a.m. - 6:00 p.m.\n"
    "Sábado: 6:30 a.m. - 3:00 p.m.\n"
    "Domingo: Cerrado"
)


SUCURSALES_ANALIZA = (
    {
        "nombre": "Tres Caminos",
        "municipio": "0801",
        "telefono": "3276-1262",
        "horario": HORARIO_600_600_DOMINGO_1,
        "direccion": (
            "Col. Tres Caminos, calle principal, antiguo local de Fundevi."
        ),
    },
    {
        "nombre": "Hospital Escuela",
        "municipio": "0801",
        "telefono": "3170-8758",
        "horario": HORARIO_630_500,
        "direccion": (
            "Plaza Martha, frente a la salida de Emergencia del Hospital "
            "Escuela, contiguo a Farmacia El Sol."
        ),
    },
    {
        "nombre": "Ciudad Nueva",
        "municipio": "0801",
        "telefono": "9825-8721",
        "horario": HORARIO_600_500_DOMINGO,
        "direccion": "Plaza Ciudad Nueva, local 12, calle Los Alcaldes.",
    },
    {
        "nombre": "Centro Tegucigalpa",
        "aliases": ("Centro", "Sucursal Centro"),
        "municipio": "0801",
        "telefono": "3260-2954",
        "horario": HORARIO_630_400,
        "direccion": (
            "Media cuadra antes del parque Valle, edificio de Clínicas "
            "San Francisco."
        ),
    },
    {
        "nombre": "Blvd. Morazán",
        "municipio": "0801",
        "telefono": "8966-0901",
        "horario": HORARIO_630_500,
        "direccion": (
            "200 metros adelante de los puentes del Blvd. Morazán, contiguo "
            "a Siman."
        ),
    },
    {
        "nombre": "Plaza Tracoma",
        "municipio": "0801",
        "telefono": "8966-1643",
        "horario": HORARIO_630_500,
        "direccion": "Km. 1, carretera de Tegucigalpa a Valle de Ángeles.",
    },
    {
        "nombre": "Aeroplaza",
        "municipio": "0801",
        "telefono": "3241-4808",
        "horario": HORARIO_600_500,
        "direccion": (
            "Comercial Aeroplaza, local 2, contiguo al Aeropuerto Toncontín."
        ),
    },
    {
        "nombre": "San Miguel",
        "municipio": "0801",
        "telefono": "8939-0099",
        "horario": HORARIO_600_500,
        "direccion": (
            "Calle principal, frente a bodega de Ferretería López, contiguo "
            "a Pronto Minix."
        ),
    },
    {
        "nombre": "Kennedy",
        "municipio": "0801",
        "telefono": "3260-9719",
        "horario": HORARIO_630_500,
        "direccion": "Segunda entrada de la colonia Kennedy, frente a Hospimed.",
    },
    {
        "nombre": "Hato",
        "municipio": "0801",
        "telefono": "8939-2946",
        "horario": HORARIO_630_500,
        "direccion": (
            "Calle principal, contiguo a Farmacity, frente a carnicería Modelo."
        ),
    },
    {
        "nombre": "Santa Fe",
        "municipio": "0801",
        "telefono": "9373-7715",
        "horario": HORARIO_600_500_DOMINGO,
        "direccion": "Colonia Santa Fe, contiguo a restaurante chino Tom-Mi.",
    },
    {
        "nombre": "Comayagüela",
        "municipio": "0801",
        "telefono": "8966-4713",
        "horario": HORARIO_630_500,
        "direccion": (
            "Barrio Concepción, 7ma avenida, entre 10 y 11 calle, Plaza "
            "Firenze, contiguo a C807 Express."
        ),
    },
    {
        "nombre": "La Granja",
        "municipio": "0801",
        "telefono": "3260-3747",
        "horario": HORARIO_630_500,
        "direccion": (
            "Barrio La Granja, Plaza La Primavera, contiguo a Ferroservi Total."
        ),
    },
    {
        "nombre": "City Plaza",
        "municipio": "0801",
        "telefono": "8841-7388",
        "horario": HORARIO_630_500,
        "direccion": "City Place, anillo periférico, sector El Sauce.",
    },
    {
        "nombre": "Loarque",
        "municipio": "0801",
        "telefono": "3260-1623",
        "horario": HORARIO_630_500,
        "direccion": (
            "Centro Comercial Paseo Loarque, frente a oficinas de El Heraldo."
        ),
    },
    {
        "nombre": "Plaza Nova",
        "aliases": ("Nova Oriente", "Sucursal Nova Oriente"),
        "municipio": "0801",
        "telefono": "3232-0379",
        "horario": HORARIO_630_500,
        "direccion": (
            "Km. 3, carretera a Danlí, 100 metros antes de la posta, Plaza Nova."
        ),
    },
    {
        "nombre": "Plaza Valencia",
        "municipio": "0801",
        "telefono": "3178-7620",
        "horario": HORARIO_630_500,
        "direccion": (
            "Col. América, avenida Los Ángeles, a un costado de la Casa Ramón "
            "Matta."
        ),
    },
    {
        "nombre": "Zonal Belén",
        "municipio": "0801",
        "telefono": "8841-7003",
        "horario": HORARIO_630_500,
        "direccion": (
            "Boulevard del Norte, segunda entrada de la colonia Las Mercedes, "
            "esquina opuesta a Banco del Pais (BANPAIS)."
        ),
    },
    {
        "nombre": "Blvd. del Norte",
        "municipio": "0501",
        "telefono": "8966-9492",
        "horario": HORARIO_600_600_DOMINGO_12,
        "direccion": "Boulevard del Norte, contiguo a la 105 Brigada.",
    },
    {
        "nombre": "Choloma",
        "municipio": "0502",
        "telefono": "3365-1203",
        "horario": HORARIO_630_500,
        "direccion": (
            "Barrio El Centro, primera calle, entre primera y segunda avenida, "
            "frente al Parque Central."
        ),
    },
    {
        "nombre": "Catarino",
        "municipio": "0501",
        "telefono": "3260-2389",
        "horario": HORARIO_600_500_DOMINGO,
        "direccion": (
            "Potosí, primera calle, frente al Hospital Mario Catarino Rivas."
        ),
    },
    {
        "nombre": "López Arellano",
        "municipio": "0502",
        "telefono": "3143-7052",
        "horario": HORARIO_630_500,
        "direccion": (
            "Brisas del Paraíso, calle principal, Plaza La Esperanza, local 8."
        ),
    },
    {
        "nombre": "Calpules",
        "municipio": "0512",
        "telefono": "3170-8741",
        "horario": HORARIO_630_500,
        "direccion": "Centro Comercial Calpules, frente a Zip Calpules.",
    },
    {
        "nombre": "Leonardo Martínez",
        "municipio": "0501",
        "telefono": "3365-5545",
        "horario": HORARIO_630_500,
        "direccion": (
            "Barrio El Benque, 10 calle, 10 avenida SO, Plaza WIP, local 11, "
            "primer nivel."
        ),
    },
    {
        "nombre": "Hospital del Sur (Choluteca)",
        "municipio": "0601",
        "telefono": "3382-9916",
        "horario": HORARIO_600_600,
        "direccion": (
            "Blvd. del Hospital, calle Roosevelt, una cuadra al este del "
            "Hospital del Sur."
        ),
    },
    {
        "nombre": "San Lorenzo",
        "municipio": "1709",
        "telefono": "3370-4436",
        "horario": HORARIO_630_400,
        "direccion": "Colonia Morazán, una cuadra antes del Hospital San Lorenzo.",
    },
    {
        "nombre": "Blvd. Mauricio Oliva (Choluteca)",
        "municipio": "0601",
        "telefono": "3365-8010",
        "horario": HORARIO_630_500,
        "direccion": (
            "Blvd. Mauricio Oliva, Plaza Chenda, contiguo a Motomundo Unimall."
        ),
    },
    {
        "nombre": "San Marcos",
        "municipio": "0615",
        "telefono": "8841-8549",
        "horario": HORARIO_630_400,
        "direccion": "Barrio El Cafetal, contiguo a Motomundo.",
    },
    {
        "nombre": "Comayagua #1",
        "municipio": "0301",
        "telefono": "3331-2757",
        "horario": HORARIO_630_600,
        "direccion": (
            "Colonia Brisas de Humuya, esquina opuesta al Hospital Santa Teresa."
        ),
    },
    {
        "nombre": "Blvd. Roberto Romero Larios",
        "municipio": "0301",
        "telefono": "3143-0780",
        "horario": HORARIO_630_500,
        "direccion": (
            "Calle principal, una cuadra abajo de Ferreteria Mega Famaco, "
            "contiguo a Farmacias Elohim Comayagua."
        ),
    },
    {
        "nombre": "Danlí",
        "municipio": "0703",
        "telefono": "3241-6794",
        "horario": HORARIO_630_500,
        "direccion": (
            "Barrio El Centro, frente a escuela Manuel de Adalid Gamero, "
            "edificio Casa Vieja."
        ),
    },
    {
        "nombre": "El Paraíso",
        "municipio": "0704",
        "telefono": "8841-8121",
        "horario": HORARIO_630_400,
        "direccion": (
            "Calle principal, Centro Comercial Paseo Los Arcos, frente a la "
            "gasolinera Uno."
        ),
    },
    {
        "nombre": "Zamorano",
        "municipio": "0817",
        "telefono": "8939-2322",
        "horario": HORARIO_630_400,
        "direccion": (
            "Estación de servicio Texaco El Zamorano, valle del Zamorano, km. "
            "29 de la carretera CA-6, local 4."
        ),
    },
)


ALIASES_SUCURSALES_ANALIZA = {
    "Tres Caminos": ("TEG - Tres Caminos",),
    "Hospital Escuela": ("TEG - Hospital Escuela",),
    "Ciudad Nueva": ("TEG - Ciudad Nueva",),
    "Centro Tegucigalpa": ("Centro", "Sucursal Centro", "TEG - Centro"),
    "Blvd. Morazán": ("TEG - Boulevard Morazán",),
    "Plaza Tracoma": ("TEG - Plaza Tracoma",),
    "Aeroplaza": ("TEG - Aeroplaza",),
    "San Miguel": ("TEG - San Miguel",),
    "Kennedy": ("TEG - Kennedy",),
    "Hato": ("TEG - Hato de Enmedio",),
    "Santa Fe": ("TEG - Santa Fe",),
    "Comayagüela": ("TEG - Comayaguela",),
    "La Granja": ("TEG - La Granja",),
    "City Plaza": ("TEG - City Plaza",),
    "Loarque": ("TEG - Loarque",),
    "Plaza Nova": (
        "Nova Oriente",
        "Plaza Nova Oriente",
        "Sucursal Nova Oriente",
    ),
    "Plaza Valencia": ("TEG - Sucursal Valencia",),
    "Blvd. del Norte": ("SPS - Boulevard del Norte",),
    "Choloma": ("SPS - Sucursal Choloma",),
    "Catarino": ("SPS - Catarino",),
    "López Arellano": ("SPS - Analiza Lopez Arellano",),
    "Calpules": ("SPS - Calpules",),
    "Leonardo Martínez": ("SPS - Hospital Leonardo Martinez",),
    "Hospital del Sur (Choluteca)": ("Hospital de sur",),
    "San Lorenzo": ("SL - Analiza San Lorenzo",),
    "Blvd. Mauricio Oliva (Choluteca)": ("Analiza Blv Mauricio Oliva",),
    "San Marcos": ("CHL - San Marcos de Colon",),
    "Comayagua #1": ("Comayagua",),
    "Blvd. Roberto Romero Larios": ("Boulevard Roberto Romero Larios",),
    "Danlí": ("Danli",),
    "El Paraíso": ("PSO - El Paraiso",),
    "Zamorano": ("TEG - El Zamorano",),
}


def normalizar_nombre(valor):
    valor = unicodedata.normalize("NFKD", valor or "")
    valor = "".join(
        " " if unicodedata.category(caracter).startswith("P") else caracter
        for caracter in valor
        if not unicodedata.combining(caracter)
    )
    return " ".join(valor.casefold().strip().split())


class Command(BaseCommand):
    help = (
        "Importa y actualiza las sucursales de Analiza documentadas en "
        "docs/Sucursales con toda la info actual (1).pdf."
    )

    def add_arguments(self, parser):
        parser.add_argument("--empresa-slug", default="Analiza")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        slug = options["empresa_slug"]
        empresa = Empresa.objects.filter(slug__iexact=slug).first()
        if not empresa:
            raise CommandError(f"No existe una empresa con slug {slug!r}.")

        codigos = {item["municipio"] for item in SUCURSALES_ANALIZA}
        municipios = {
            municipio.codigo: municipio
            for municipio in Municipio.objects.filter(codigo__in=codigos)
        }
        faltantes = sorted(codigos - municipios.keys())
        if faltantes:
            raise CommandError(
                "Faltan municipios. Ejecuta migrate antes de importar: "
                + ", ".join(faltantes)
            )

        with transaction.atomic():
            creadas, actualizadas = self._sincronizar(empresa, municipios)
            if options["dry_run"]:
                transaction.set_rollback(True)
                self.stdout.write(
                    self.style.WARNING(
                        f"Simulacion: {creadas} por crear y {actualizadas} por "
                        "actualizar. No se escribieron datos."
                    )
                )
                return

        self.stdout.write(
            self.style.SUCCESS(
                f"Sucursales sincronizadas: {creadas} creadas y "
                f"{actualizadas} actualizadas."
            )
        )

    def _sincronizar(self, empresa, municipios):
        existentes = list(SucursalEmpresa.objects.filter(empresa=empresa))
        por_nombre = {
            normalizar_nombre(sucursal.nombre): sucursal
            for sucursal in existentes
        }
        sincronizadas = set()
        creadas = 0
        actualizadas = 0

        for orden, datos in enumerate(SUCURSALES_ANALIZA, start=1):
            nombres = (
                datos["nombre"],
                *datos.get("aliases", ()),
                *ALIASES_SUCURSALES_ANALIZA.get(datos["nombre"], ()),
            )
            coincidencias = {
                por_nombre[nombre_normalizado].pk: por_nombre[nombre_normalizado]
                for nombre in nombres
                if (nombre_normalizado := normalizar_nombre(nombre)) in por_nombre
            }
            if len(coincidencias) > 1:
                raise CommandError(
                    f"Hay varias sucursales equivalentes para {datos['nombre']!r}."
                )

            sucursal = next(iter(coincidencias.values()), None)
            valores = {
                "nombre": datos["nombre"],
                "municipio": municipios[datos["municipio"]],
                "direccion": datos["direccion"],
                "telefono": datos["telefono"],
                "horario": datos["horario"],
                "orden": orden,
                "estado": SucursalEmpresa.Estado.ACTIVA,
                "activa": True,
            }
            if sucursal:
                campos_cambiados = []
                for campo, valor in valores.items():
                    valor_actual = (
                        sucursal.municipio_id
                        if campo == "municipio"
                        else getattr(sucursal, campo)
                    )
                    valor_esperado = valor.pk if campo == "municipio" else valor
                    if valor_actual != valor_esperado:
                        setattr(sucursal, campo, valor)
                        campos_cambiados.append(campo)
                if campos_cambiados:
                    sucursal.save(update_fields=campos_cambiados)
                    actualizadas += 1
            else:
                sucursal = SucursalEmpresa.objects.create(
                    empresa=empresa,
                    **valores,
                )
                creadas += 1

            sincronizadas.add(sucursal.pk)
            por_nombre[normalizar_nombre(datos["nombre"])] = sucursal

        adicionales = sorted(
            (
                sucursal
                for sucursal in existentes
                if sucursal.pk not in sincronizadas
            ),
            key=lambda sucursal: (sucursal.orden, sucursal.pk),
        )
        for orden, sucursal in enumerate(
            adicionales,
            start=len(SUCURSALES_ANALIZA) + 1,
        ):
            if sucursal.orden != orden:
                sucursal.orden = orden
                sucursal.save(update_fields=["orden"])
                actualizadas += 1

        return creadas, actualizadas
