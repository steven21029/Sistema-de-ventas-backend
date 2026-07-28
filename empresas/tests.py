from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Empresa, SucursalEmpresa


class EmpresaActualAPITests(APITestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Analiza Laboratorios Clinicos",
            slug="Analiza",
            subdominio="analiza",
            dominio_personalizado="tienda.analizahn.com",
        )

    def test_resuelve_empresa_por_subdominio_localhost(self):
        response = self.client.get(
            reverse("empresas-actual"),
            {"host": "analiza.localhost:3000"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["slug"], self.empresa.slug)
        self.assertEqual(response.data["subdominio"], "analiza")
        self.assertEqual(len(response.data["menu"]), 7)

    def test_resuelve_empresa_por_dominio_personalizado(self):
        response = self.client.get(
            reverse("empresas-actual"),
            {"host": "https://tienda.analizahn.com:443/inicio"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["slug"], self.empresa.slug)
        self.assertEqual(
            response.data["dominio_personalizado"],
            "tienda.analizahn.com",
        )

    def test_resuelve_empresa_por_slug_como_respaldo(self):
        response = self.client.get(
            reverse("empresas-actual"),
            {"slug": self.empresa.slug},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["slug"], self.empresa.slug)

    def test_no_resuelve_empresa_inactiva(self):
        self.empresa.activa = False
        self.empresa.save(update_fields=["activa"])

        response = self.client.get(
            reverse("empresas-actual"),
            {"host": "analiza.localhost:3000"},
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_menu_endpoint_devuelve_menu_configurable_por_empresa(self):
        item = self.empresa.items_menu.get(clave="examenes")
        item.texto = "Productos"
        item.ruta = "/productos"
        item.save(update_fields=["texto", "ruta", "fecha_actualizacion"])
        self.empresa.items_menu.filter(clave="sucursales").update(activo=False)

        response = self.client.get(
            reverse("empresas-menu"),
            {"empresa_slug": self.empresa.slug},
        )

        textos = [item["texto"] for item in response.data]
        rutas = {item["clave"]: item["ruta"] for item in response.data}
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Productos", textos)
        self.assertNotIn("Sucursales", textos)
        self.assertEqual(rutas["examenes"], "/productos")

    def test_menu_endpoint_resuelve_por_host(self):
        response = self.client.get(
            reverse("empresas-menu"),
            {"host": "analiza.localhost:3000"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["clave"], "inicio")

    def test_sucursales_publicas_por_empresa_slug_y_busqueda(self):
        SucursalEmpresa.objects.create(
            empresa=self.empresa,
            nombre="Sucursal Centro",
            direccion="Centro comercial",
            telefono="22222222",
            horario="Lunes a viernes",
            google_maps_url="https://maps.google.com/example",
            imagen_url="https://example.com/sucursal-centro.jpg",
        )
        SucursalEmpresa.objects.create(
            empresa=self.empresa,
            nombre="Sucursal inactiva",
            direccion="No visible",
            activa=False,
        )

        response = self.client.get(
            reverse("empresas-sucursales"),
            {
                "empresa_slug": self.empresa.slug,
                "buscar": "centro",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["nombre"], "Sucursal Centro")
        self.assertIsNone(response.data[0]["imagen_final"])
        self.assertNotIn("imagen_url", response.data[0])
        self.assertNotIn("id", response.data[0])

    def test_sucursales_usan_imagen_general_de_empresa(self):
        self.empresa.imagen_sucursales_url = "https://example.com/sucursales-general.jpg"
        self.empresa.save(update_fields=["imagen_sucursales_url", "fecha_actualizacion"])
        SucursalEmpresa.objects.create(
            empresa=self.empresa,
            nombre="Sucursal Centro",
            direccion="Centro comercial",
            imagen_url="https://example.com/sucursal-individual.jpg",
        )

        response = self.client.get(
            reverse("empresas-sucursales"),
            {"empresa_slug": self.empresa.slug},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data[0]["imagen_final"],
            "https://example.com/sucursales-general.jpg",
        )

    def test_empresa_publica_devuelve_imagen_general_de_sucursales(self):
        self.empresa.imagen_sucursales_url = "https://example.com/sucursales-general.jpg"
        self.empresa.save(update_fields=["imagen_sucursales_url", "fecha_actualizacion"])

        response = self.client.get(
            reverse("empresas-actual"),
            {"slug": self.empresa.slug},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["imagen_sucursales_final"],
            "https://example.com/sucursales-general.jpg",
        )

    def test_sucursales_aceptan_coordenadas_largas(self):
        latitud = Decimal("14.083697123456789")
        longitud = Decimal("-87.206811987654321")
        precision_practica = Decimal("0.000000000001")
        SucursalEmpresa.objects.create(
            empresa=self.empresa,
            nombre="Sucursal Coordenadas",
            direccion="Direccion con ubicacion exacta",
            latitud=latitud,
            longitud=longitud,
        )

        response = self.client.get(
            reverse("empresas-sucursales"),
            {"empresa_slug": self.empresa.slug},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            Decimal(response.data[0]["latitud"]).quantize(precision_practica),
            latitud.quantize(precision_practica),
        )
        self.assertEqual(
            Decimal(response.data[0]["longitud"]).quantize(precision_practica),
            longitud.quantize(precision_practica),
        )
