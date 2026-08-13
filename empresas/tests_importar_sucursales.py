from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from empresas.models import Empresa, SucursalEmpresa


class ImportarSucursalesAnalizaTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Analiza",
            slug="Analiza",
        )

    def test_importacion_es_idempotente_y_conserva_datos_geograficos(self):
        centro = SucursalEmpresa.objects.create(
            empresa=self.empresa,
            nombre="Centro",
            ciudad="",
            direccion="Direccion provisional",
            telefono="00000000",
            google_maps_url="https://maps.example/centro",
            latitud="14.100000000000000",
            longitud="-87.200000000000000",
        )
        nova = SucursalEmpresa.objects.create(
            empresa=self.empresa,
            nombre="Nova Oriente",
            ciudad="",
            direccion="Direccion provisional",
            telefono="11111111",
            google_maps_url="https://maps.example/nova",
        )
        calle_real = SucursalEmpresa.objects.create(
            empresa=self.empresa,
            nombre="Calle Real",
            ciudad="",
            direccion="Sucursal adicional",
            telefono="9999-9999",
            orden=3,
        )

        call_command("importar_sucursales_analiza", stdout=StringIO())
        segunda_salida = StringIO()
        call_command("importar_sucursales_analiza", stdout=segunda_salida)

        self.assertEqual(
            SucursalEmpresa.objects.filter(empresa=self.empresa).count(),
            34,
        )
        centro.refresh_from_db()
        nova.refresh_from_db()
        calle_real.refresh_from_db()
        self.assertEqual(centro.nombre, "Centro Tegucigalpa")
        self.assertEqual(centro.municipio.codigo, "0801")
        self.assertEqual(centro.ciudad, "Distrito Central")
        self.assertEqual(centro.telefono, "3260-2954")
        self.assertEqual(centro.google_maps_url, "https://maps.example/centro")
        self.assertEqual(str(centro.latitud), "14.100000000000000")
        self.assertEqual(nova.nombre, "Plaza Nova")
        self.assertEqual(nova.telefono, "3232-0379")
        self.assertEqual(nova.google_maps_url, "https://maps.example/nova")
        self.assertEqual(calle_real.nombre, "Calle Real")
        self.assertEqual(calle_real.telefono, "9999-9999")
        self.assertEqual(calle_real.orden, 34)
        self.assertIn(
            "0 creadas y 0 actualizadas",
            segunda_salida.getvalue(),
        )

        hospital = SucursalEmpresa.objects.get(
            empresa=self.empresa,
            nombre="Hospital Escuela",
        )
        self.assertEqual(hospital.telefono, "3170-8758")
        self.assertIn("Farmacia El Sol", hospital.direccion)
        self.assertEqual(hospital.estado, SucursalEmpresa.Estado.ACTIVA)

        calpules = SucursalEmpresa.objects.get(
            empresa=self.empresa,
            nombre="Calpules",
        )
        zamorano = SucursalEmpresa.objects.get(
            empresa=self.empresa,
            nombre="Zamorano",
        )
        self.assertEqual(calpules.municipio.codigo, "0512")
        self.assertEqual(zamorano.municipio.codigo, "0817")

    def test_dry_run_no_escribe_datos(self):
        salida = StringIO()
        call_command(
            "importar_sucursales_analiza",
            dry_run=True,
            stdout=salida,
        )

        self.assertFalse(
            SucursalEmpresa.objects.filter(empresa=self.empresa).exists()
        )
        self.assertIn("No se escribieron datos", salida.getvalue())
