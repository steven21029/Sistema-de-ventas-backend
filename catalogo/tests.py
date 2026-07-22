from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from empresas.models import Empresa
from .models import Categoria, Familia, PaqueteCatalogo, PaqueteProducto, Producto


class CatalogoPaginasPublicasTests(APITestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Analiza Laboratorios Clinicos",
            slug="Analiza",
            subdominio="analiza",
        )
        self.familia = Familia.objects.create(
            empresa=self.empresa,
            nombre="Examenes",
            descripcion="Servicios de laboratorio",
            imagen_url="https://example.com/familia.jpg",
        )
        self.categoria = Categoria.objects.create(
            empresa=self.empresa,
            familia=self.familia,
            nombre="Hematologia",
        )
        self.producto = Producto.objects.create(
            empresa=self.empresa,
            familia=self.familia,
            categoria=self.categoria,
            codigo_barra="HEMO-001",
            nombre="Hemograma completo",
            descripcion="Examen hematologico",
            precio="150.00",
            imagen_url="https://example.com/hemograma.jpg",
        )
        Producto.objects.filter(pk=self.producto.pk).update(existencia=10)
        self.producto.refresh_from_db()

    def test_examenes_publicos_por_empresa_slug_y_busqueda(self):
        response = self.client.get(
            reverse("catalogo-examenes"),
            {
                "empresa_slug": self.empresa.slug,
                "buscar": "hemo",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["codigo_barra"], self.producto.codigo_barra)
        self.assertEqual(response.data[0]["imagen_final"], self.producto.imagen_url)
        self.assertNotIn("id", response.data[0])

    def test_servicios_publicos_devuelven_familias_activas(self):
        response = self.client.get(
            reverse("catalogo-servicios"),
            {"empresa_slug": self.empresa.slug},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["nombre"], self.familia.nombre)
        self.assertEqual(response.data[0]["imagen_final"], self.familia.imagen_url)
        self.assertEqual(response.data[0]["cantidad_productos"], 1)

    def test_combos_destacados_publicos(self):
        combo = PaqueteCatalogo.objects.create(
            empresa=self.empresa,
            tipo=PaqueteCatalogo.Tipo.COMBO,
            codigo="COMBO-001",
            nombre="Combo preventivo",
            precio_normal="500.00",
            precio_paquete="399.00",
            porcentaje_descuento=20,
            imagen_url="https://example.com/combo.jpg",
            destacado=True,
        )
        PaqueteProducto.objects.create(paquete=combo, producto=self.producto)

        response = self.client.get(
            reverse("catalogo-combos-destacados"),
            {"empresa_slug": self.empresa.slug},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["codigo"], combo.codigo)
        self.assertEqual(response.data[0]["precio_combo"], "399.00")
        self.assertEqual(response.data[0]["productos"][0]["codigo_barra"], "HEMO-001")

    def test_perfiles_publicos(self):
        perfil = PaqueteCatalogo.objects.create(
            empresa=self.empresa,
            tipo=PaqueteCatalogo.Tipo.PERFIL,
            codigo="PERFIL-001",
            nombre="Perfil ejecutivo",
            precio_normal="700.00",
            precio_paquete="600.00",
            porcentaje_descuento=14,
        )
        PaqueteProducto.objects.create(paquete=perfil, producto=self.producto)

        response = self.client.get(
            reverse("catalogo-perfiles"),
            {
                "empresa_slug": self.empresa.slug,
                "buscar": "ejecutivo",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["codigo"], perfil.codigo)
        self.assertEqual(response.data[0]["precio_perfil"], "600.00")
        self.assertEqual(response.data[0]["productos"][0]["precio"], "150.00")

    def test_productos_mas_vendidos_publicos(self):
        response = self.client.get(
            reverse("catalogo-productos-mas-vendidos"),
            {"empresa_slug": self.empresa.slug},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["codigo_barra"], self.producto.codigo_barra)
