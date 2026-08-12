from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class UbicacionesMunicipiosMigrationTests(TransactionTestCase):
    migrate_from = [("empresas", "0018_empresa_pago_en_linea")]
    migrate_to = [("empresas", "0020_normalizar_orden_municipios")]

    def setUp(self):
        super().setUp()
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_from)
        apps = self.executor.loader.project_state(self.migrate_from).apps

        Empresa = apps.get_model("empresas", "Empresa")
        SucursalEmpresa = apps.get_model("empresas", "SucursalEmpresa")

        analiza = Empresa.objects.create(nombre="Analiza", slug="analiza")
        self.analiza_id = analiza.pk

        SucursalEmpresa.objects.create(
            empresa=analiza,
            nombre="Sucursal Centro",
            ciudad="Distrito Central",
            direccion="Centro",
        )
        SucursalEmpresa.objects.create(
            empresa=analiza,
            nombre="Sucursal Centro duplicada",
            ciudad="distrito central",
            direccion="Centro 2",
        )
        SucursalEmpresa.objects.create(
            empresa=analiza,
            nombre="Sucursal Cholona",
            ciudad="Cholona",
            direccion="Cortes",
        )
        SucursalEmpresa.objects.create(
            empresa=analiza,
            nombre="Sucursal Zamorano",
            ciudad="Zamorano",
            direccion="Zamorano",
        )
        SucursalEmpresa.objects.create(
            empresa=analiza,
            nombre="Sucursal La Ceiba",
            ciudad="La Ceiba",
            direccion="La Ceiba",
            activa=False,
        )
        SucursalEmpresa.objects.create(
            empresa=analiza,
            nombre="Sucursal sin ciudad",
            ciudad="",
            direccion="Sin ciudad",
        )

        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_to)
        self.apps = self.executor.loader.project_state(self.migrate_to).apps

    def test_puebla_catalogo_y_relaciona_sucursales_existentes(self):
        Departamento = self.apps.get_model("empresas", "Departamento")
        Municipio = self.apps.get_model("empresas", "Municipio")
        SucursalEmpresa = self.apps.get_model("empresas", "SucursalEmpresa")

        self.assertEqual(Departamento.objects.count(), 18)
        self.assertEqual(Municipio.objects.count(), 298)

        distrito = Municipio.objects.get(codigo="0801")
        comayagua = Municipio.objects.get(codigo="0301")
        sps = Municipio.objects.get(codigo="0501")
        choluteca = Municipio.objects.get(codigo="0601")
        self.assertEqual(distrito.nombre, "Distrito Central")
        self.assertEqual(
            [distrito.orden, comayagua.orden, sps.orden, choluteca.orden],
            [1, 2, 3, 4],
        )
        self.assertEqual(Municipio.objects.order_by("-orden").first().orden, 298)

        centro = SucursalEmpresa.objects.get(nombre="Sucursal Centro")
        duplicada = SucursalEmpresa.objects.get(nombre="Sucursal Centro duplicada")
        cholona = SucursalEmpresa.objects.get(nombre="Sucursal Cholona")
        zamorano = SucursalEmpresa.objects.get(nombre="Sucursal Zamorano")
        la_ceiba = SucursalEmpresa.objects.get(nombre="Sucursal La Ceiba")
        sin_ciudad = SucursalEmpresa.objects.get(nombre="Sucursal sin ciudad")

        self.assertEqual(centro.municipio_id, distrito.pk)
        self.assertEqual(duplicada.municipio_id, distrito.pk)
        self.assertEqual(cholona.municipio.codigo, "0502")
        self.assertEqual(zamorano.municipio.codigo, "0817")
        self.assertEqual(la_ceiba.municipio.codigo, "0101")
        self.assertEqual(la_ceiba.estado, "inactiva")
        self.assertIsNone(sin_ciudad.municipio_id)
