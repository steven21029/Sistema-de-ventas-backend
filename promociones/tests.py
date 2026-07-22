from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from empresas.models import Empresa
from usuarios.models import PerfilUsuario
from .models import BannerPromocional


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
