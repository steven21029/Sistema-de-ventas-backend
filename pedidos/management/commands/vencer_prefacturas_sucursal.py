from django.core.management.base import BaseCommand, CommandError

from empresas.models import Empresa
from pedidos.vencimientos import vencer_prefacturas_sucursal


class Command(BaseCommand):
    help = (
        "Rechaza pedidos y pagos en sucursal cuyas prefacturas superaron su vigencia."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--empresa-slug",
            dest="empresa_slug",
            help="Limita el proceso a una empresa.",
        )

    def handle(self, *args, **options):
        empresa_ids = None
        empresa_slug = (options.get("empresa_slug") or "").strip()
        if empresa_slug:
            empresa = Empresa.objects.filter(slug__iexact=empresa_slug).first()
            if not empresa:
                raise CommandError("No existe una empresa con ese slug.")
            empresa_ids = [empresa.pk]

        resultado = vencer_prefacturas_sucursal(empresa_ids=empresa_ids)
        self.stdout.write(
            self.style.SUCCESS(
                "Proceso completado: "
                f"{resultado['pedidos_rechazados']} pedidos y "
                f"{resultado['pagos_rechazados']} pagos rechazados."
            )
        )
