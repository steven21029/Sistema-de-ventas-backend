from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from catalogo.datos.descripciones_examenes import DESCRIPCIONES_EXAMENES
from catalogo.models import Familia, Producto
from empresas.models import Empresa


class Command(BaseCommand):
    help = (
        "Agrega descripciones informativas de seis palabras a los examenes "
        "importados de una empresa."
    )

    def add_arguments(self, parser):
        parser.add_argument("--empresa-slug", default="Analiza")
        parser.add_argument("--familia", default="Examenes")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Valida y muestra el resumen sin guardar cambios.",
        )

    def handle(self, *args, **options):
        self._validar_catalogo()

        empresa = Empresa.objects.filter(
            slug__iexact=options["empresa_slug"].strip()
        ).first()
        if not empresa:
            raise CommandError(
                f"No existe la empresa con slug {options['empresa_slug']}."
            )

        familia = Familia.objects.filter(
            empresa=empresa,
            nombre__iexact=options["familia"].strip(),
        ).first()
        if not familia:
            raise CommandError(
                f"No existe la familia {options['familia']} en {empresa.nombre}."
            )

        productos = {
            producto.codigo_barra: producto
            for producto in Producto.objects.filter(
                empresa=empresa,
                familia=familia,
                codigo_barra__in=DESCRIPCIONES_EXAMENES,
            )
        }
        codigos_faltantes = sorted(set(DESCRIPCIONES_EXAMENES) - set(productos))
        if codigos_faltantes:
            raise CommandError(
                "Faltan examenes esperados en la base de datos: "
                + ", ".join(codigos_faltantes)
            )

        por_actualizar = []
        sin_cambios = 0
        fecha_actualizacion = timezone.now()
        for codigo, descripcion in DESCRIPCIONES_EXAMENES.items():
            producto = productos[codigo]
            if producto.descripcion == descripcion:
                sin_cambios += 1
                continue

            producto.descripcion = descripcion
            producto.fecha_actualizacion = fecha_actualizacion
            por_actualizar.append(producto)

        self.stdout.write(
            f"Examenes validados: {len(productos)}; "
            f"por actualizar: {len(por_actualizar)}; "
            f"sin cambios: {sin_cambios}."
        )

        if options["dry_run"]:
            self.stdout.write(
                self.style.WARNING("Simulacion finalizada: no se guardaron cambios.")
            )
            return

        with transaction.atomic():
            Producto.objects.bulk_update(
                por_actualizar,
                ["descripcion", "fecha_actualizacion"],
                batch_size=200,
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Descripciones actualizadas correctamente: {len(por_actualizar)}."
            )
        )

    def _validar_catalogo(self):
        if len(DESCRIPCIONES_EXAMENES) != 328:
            raise CommandError(
                "El catalogo debe contener exactamente 328 descripciones."
            )

        cantidades_invalidas = {
            codigo: len(descripcion.split())
            for codigo, descripcion in DESCRIPCIONES_EXAMENES.items()
            if len(descripcion.split()) != 6
        }
        if cantidades_invalidas:
            detalle = ", ".join(
                f"{codigo}: {cantidad}"
                for codigo, cantidad in cantidades_invalidas.items()
            )
            raise CommandError(
                "Cada descripcion debe tener exactamente seis palabras: "
                + detalle
            )
