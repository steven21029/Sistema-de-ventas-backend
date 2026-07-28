from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from catalogo.models import Categoria, Familia, Producto
from empresas.models import Empresa
from usuarios.models import PerfilUsuario
from .models import BannerPromocional, OfertaProducto, OfertaPromocional


class BannerPromocionalAPITests(APITestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Analiza Laboratorios Clinicos",
            slug="Analiza",
        )
        self.banner_activo = BannerPromocional.objects.create(
            empresa=self.empresa,
            titulo="Banner activo",
            imagen_url="https://example.com/activo.jpg",
            url_boton="/promociones/oferta-001",
            activo=True,
        )
        self.banner_inactivo = BannerPromocional.objects.create(
            empresa=self.empresa,
            titulo="Banner inactivo",
            imagen_url="https://example.com/inactivo.jpg",
            activo=False,
        )
        self.usuario = get_user_model().objects.create_user(
            username="admin@analiza.test",
            email="admin@analiza.test",
            password="ClaveSegura123!",
        )
        self.usuario.perfil.empresa = self.empresa
        self.usuario.perfil.rol = PerfilUsuario.Rol.ADMINISTRADOR_EMPRESA
        self.usuario.perfil.activo = True
        self.usuario.perfil.correo_verificado = True
        self.usuario.perfil.save()

    def test_publico_no_devuelve_banners_inactivos(self):
        response = self.client.get(
            reverse("promociones-banners-list"),
            {"empresa_slug": self.empresa.slug},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["titulo"], self.banner_activo.titulo)
        self.assertEqual(response.data[0]["url_boton"], "/promociones/oferta-001")

    def test_admin_sin_incluir_inactivos_tampoco_devuelve_inactivos(self):
        self.client.force_authenticate(self.usuario)

        response = self.client.get(
            reverse("promociones-banners-list"),
            {"empresa_slug": self.empresa.slug},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["titulo"], self.banner_activo.titulo)
        self.assertNotIn("activo", response.data[0])

    def test_admin_con_incluir_inactivos_devuelve_todos(self):
        self.client.force_authenticate(self.usuario)

        response = self.client.get(
            reverse("promociones-banners-list"),
            {
                "empresa_slug": self.empresa.slug,
                "incluir_inactivos": "true",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(
            {banner["titulo"] for banner in response.data},
            {self.banner_activo.titulo, self.banner_inactivo.titulo},
        )
        self.assertIn("activo", response.data[0])


class OfertaPromocionalAPITests(APITestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Analiza Laboratorios Clinicos",
            slug="Analiza",
        )
        self.familia = Familia.objects.create(
            empresa=self.empresa,
            nombre="Examenes",
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
            nombre="Hemograma",
            precio="150.00",
        )
        self.oferta = OfertaPromocional.objects.create(
            empresa=self.empresa,
            tipo=OfertaPromocional.Tipo.PRODUCTO,
            codigo="OFERTA-001",
            titulo="Hemograma en oferta",
            descripcion="Precio especial por tiempo limitado.",
            precio_normal="150.00",
            precio_oferta="120.00",
            porcentaje_descuento=20,
            imagen_url="https://example.com/oferta.jpg",
            url_destino="/promociones/oferta-001",
            activo=True,
        )
        OfertaProducto.objects.create(oferta=self.oferta, producto=self.producto)
        self.oferta_inactiva = OfertaPromocional.objects.create(
            empresa=self.empresa,
            tipo=OfertaPromocional.Tipo.PRODUCTO,
            codigo="OFERTA-002",
            titulo="Oferta inactiva",
            precio_normal="100.00",
            precio_oferta="90.00",
            activo=False,
        )
        self.usuario = get_user_model().objects.create_user(
            username="admin2@analiza.test",
            email="admin2@analiza.test",
            password="ClaveSegura123!",
        )
        self.usuario.perfil.empresa = self.empresa
        self.usuario.perfil.rol = PerfilUsuario.Rol.ADMINISTRADOR_EMPRESA
        self.usuario.perfil.activo = True
        self.usuario.perfil.correo_verificado = True
        self.usuario.perfil.save()

    def test_publico_devuelve_ofertas_activas_no_banners(self):
        response = self.client.get(
            reverse("promociones-ofertas-list"),
            {
                "empresa_slug": self.empresa.slug,
                "buscar": "hemograma",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["codigo"], self.oferta.codigo)
        self.assertEqual(response.data[0]["precio_oferta"], "120.00")
        self.assertEqual(response.data[0]["imagen_final"], self.oferta.imagen_url)
        self.assertEqual(response.data[0]["url_destino"], "/promociones/oferta-001")
        self.assertEqual(
            response.data[0]["productos"][0]["codigo_barra"],
            self.producto.codigo_barra,
        )
        self.assertNotIn("id", response.data[0])

    def test_admin_con_incluir_inactivos_ve_todas_las_ofertas(self):
        self.client.force_authenticate(self.usuario)

        response = self.client.get(
            reverse("promociones-ofertas-list"),
            {
                "empresa_slug": self.empresa.slug,
                "incluir_inactivos": "true",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertIn("activo", response.data[0])
