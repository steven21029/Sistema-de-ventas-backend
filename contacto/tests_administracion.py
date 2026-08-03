from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from empresas.models import Empresa
from usuarios.models import PerfilUsuario
from .models import MensajeContacto


User = get_user_model()


class ContactosAdministrativosAPITests(APITestCase):
    def setUp(self):
        self.analiza = Empresa.objects.create(
            nombre="Analiza",
            slug="analiza",
            subdominio="analiza",
        )
        self.otra = Empresa.objects.create(
            nombre="Otra empresa",
            slug="otra",
            subdominio="otra",
        )
        self.admin = self._crear_usuario(
            "admin",
            PerfilUsuario.Rol.ADMINISTRADOR_EMPRESA,
            self.analiza,
        )
        self.maestro = self._crear_usuario(
            "maestro",
            PerfilUsuario.Rol.ADMINISTRADOR_MAESTRO,
            None,
        )
        self.maestro.perfil.empresas_permitidas.add(self.analiza)
        self.mensaje = MensajeContacto.objects.create(
            empresa=self.analiza,
            nombre="Cliente analiza",
            correo="cliente@example.com",
            asunto="Consulta",
            mensaje="Mensaje original",
        )
        self.mensaje_otra = MensajeContacto.objects.create(
            empresa=self.otra,
            nombre="Cliente otra",
            correo="otra@example.com",
            mensaje="Mensaje externo",
        )

    def _crear_usuario(self, username, rol, empresa):
        usuario = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="Prueba12345!",
        )
        perfil = usuario.perfil
        perfil.rol = rol
        perfil.empresa = empresa
        perfil.correo_verificado = True
        perfil.activo = True
        perfil.save()
        return usuario

    def test_maestro_lista_solo_empresas_permitidas(self):
        self.client.force_authenticate(self.maestro)
        respuesta = self.client.get(reverse("contacto-mensajes-list"))

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in respuesta.data], [self.mensaje.id])

    def test_admin_solo_modifica_estado_del_mensaje(self):
        self.client.force_authenticate(self.admin)
        respuesta = self.client.patch(
            reverse("contacto-mensajes-detail", kwargs={"pk": self.mensaje.pk}),
            {
                "estado": MensajeContacto.Estado.RESPONDIDO,
                "mensaje": "Contenido alterado",
                "nombre": "Nombre alterado",
            },
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.mensaje.refresh_from_db()
        self.assertEqual(self.mensaje.estado, MensajeContacto.Estado.RESPONDIDO)
        self.assertEqual(self.mensaje.mensaje, "Mensaje original")
        self.assertEqual(self.mensaje.nombre, "Cliente analiza")

    def test_filtros_y_paginacion_administrativa(self):
        self.client.force_authenticate(self.admin)
        respuesta = self.client.get(
            reverse("contacto-mensajes-list"),
            {
                "buscar": "Consulta",
                "estado": MensajeContacto.Estado.NUEVO,
                "paginar": "true",
            },
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["count"], 1)
        self.assertEqual(respuesta.data["results"][0]["id"], self.mensaje.id)

    def test_admin_recibe_403_al_solicitar_otra_empresa(self):
        self.client.force_authenticate(self.admin)
        respuesta = self.client.get(
            reverse("contacto-mensajes-list"),
            {"empresa_slug": self.otra.slug},
        )

        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)
