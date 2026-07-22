from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from empresas.models import Empresa
from usuarios.models import PerfilUsuario
from .models import MensajeContacto


class MensajeContactoAPITests(APITestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Analiza Laboratorios Clinicos",
            slug="Analiza",
            subdominio="analiza",
        )

    def test_crea_mensaje_publico(self):
        response = self.client.post(
            reverse("contacto-mensajes-list"),
            {
                "empresa_slug": self.empresa.slug,
                "nombre": "Cliente",
                "telefono": "99999999",
                "asunto": "Consulta",
                "mensaje": "Quiero informacion.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["ok"])
        self.assertEqual(MensajeContacto.objects.count(), 1)
        self.assertEqual(MensajeContacto.objects.first().estado, MensajeContacto.Estado.NUEVO)

    def test_requiere_telefono_o_correo(self):
        response = self.client.post(
            reverse("contacto-mensajes-list"),
            {
                "empresa_slug": self.empresa.slug,
                "nombre": "Cliente",
                "mensaje": "Quiero informacion.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_empresa_lista_solo_sus_mensajes(self):
        MensajeContacto.objects.create(
            empresa=self.empresa,
            nombre="Cliente",
            telefono="99999999",
            mensaje="Hola",
        )
        usuario = get_user_model().objects.create_user(
            username="admin@analiza.test",
            email="admin@analiza.test",
            password="ClaveSegura123!",
        )
        usuario.perfil.empresa = self.empresa
        usuario.perfil.rol = PerfilUsuario.Rol.ADMINISTRADOR_EMPRESA
        usuario.perfil.activo = True
        usuario.perfil.correo_verificado = True
        usuario.perfil.save()
        self.client.force_authenticate(usuario)

        response = self.client.get(reverse("contacto-mensajes-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["empresa_slug"], self.empresa.slug)
