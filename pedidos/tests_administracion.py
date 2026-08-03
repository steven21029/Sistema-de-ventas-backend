from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from empresas.models import Empresa
from usuarios.models import PerfilUsuario
from .models import Pedido


User = get_user_model()


class PedidosAdministrativosAPITests(APITestCase):
    def setUp(self):
        self.analiza = Empresa.objects.create(
            nombre="Analiza",
            slug="analiza",
            subdominio="analiza",
            cobra_impuesto=False,
        )
        self.otra = Empresa.objects.create(
            nombre="Otra empresa",
            slug="otra",
            subdominio="otra",
            cobra_impuesto=False,
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
        self.cliente_uno = self._crear_usuario(
            "cliente-uno",
            PerfilUsuario.Rol.COMPRADOR,
            self.analiza,
        )
        self.cliente_dos = self._crear_usuario(
            "cliente-dos",
            PerfilUsuario.Rol.COMPRADOR,
            self.analiza,
        )
        self.cliente_otra = self._crear_usuario(
            "cliente-otra",
            PerfilUsuario.Rol.COMPRADOR,
            self.otra,
        )
        self.pedido_uno = self._crear_pedido(self.analiza, self.cliente_uno, "Ana")
        self.pedido_dos = self._crear_pedido(self.analiza, self.cliente_dos, "Luis")
        self.pedido_otra = self._crear_pedido(self.otra, self.cliente_otra, "Marta")

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

    def _crear_pedido(self, empresa, usuario, nombre):
        return Pedido.objects.create(
            empresa=empresa,
            usuario=usuario,
            tipo_entrega=Pedido.TipoEntrega.RETIRO_EN_LOCAL,
            nombre_recibe=nombre,
            subtotal=Decimal("100.00"),
        )

    def test_admin_empresa_ve_pedidos_de_todos_sus_clientes(self):
        self.client.force_authenticate(self.admin)
        respuesta = self.client.get(reverse("pedidos-pedidos-list"))

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        ids = {item["id"] for item in respuesta.data}
        self.assertEqual(ids, {self.pedido_uno.id, self.pedido_dos.id})

    def test_comprador_solo_ve_sus_pedidos(self):
        self.client.force_authenticate(self.cliente_uno)
        respuesta = self.client.get(reverse("pedidos-pedidos-list"))

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual([item["id"] for item in respuesta.data], [self.pedido_uno.id])

    def test_maestro_solo_ve_empresas_asignadas(self):
        self.client.force_authenticate(self.maestro)
        respuesta = self.client.get(reverse("pedidos-pedidos-list"))

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        ids = {item["id"] for item in respuesta.data}
        self.assertEqual(ids, {self.pedido_uno.id, self.pedido_dos.id})

    def test_busqueda_estado_y_paginacion(self):
        self.client.force_authenticate(self.admin)
        respuesta = self.client.get(
            reverse("pedidos-pedidos-list"),
            {
                "buscar": self.pedido_uno.numero,
                "estado": Pedido.EstadoPago.PENDIENTE,
                "paginar": "true",
            },
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["count"], 1)
        self.assertEqual(respuesta.data["results"][0]["id"], self.pedido_uno.id)

    def test_admin_no_puede_modificar_historial(self):
        self.client.force_authenticate(self.admin)
        respuesta = self.client.patch(
            reverse("pedidos-pedidos-detail", kwargs={"pk": self.pedido_uno.pk}),
            {"total": "1.00"},
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_admin_recibe_403_al_solicitar_otra_empresa(self):
        self.client.force_authenticate(self.admin)
        respuesta = self.client.get(
            reverse("pedidos-pedidos-list"),
            {"empresa_slug": self.otra.slug},
        )

        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)
