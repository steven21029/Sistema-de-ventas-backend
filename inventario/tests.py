from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from catalogo.models import Categoria, Familia, Producto
from empresas.models import Empresa
from usuarios.models import PerfilUsuario
from .models import MovimientoInventario


class InventarioAPITests(APITestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Analiza Laboratorios Clinicos",
            slug="Analiza",
        )
        self.familia = Familia.objects.create(
            empresa=self.empresa,
            nombre="Laboratorio",
        )
        self.categoria = Categoria.objects.create(
            empresa=self.empresa,
            familia=self.familia,
            nombre="Hematologia",
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
        self.client.force_authenticate(self.usuario)

    def crear_producto(self, codigo_barra, nombre, existencia_minima=0, precio="100.00"):
        return Producto.objects.create(
            empresa=self.empresa,
            familia=self.familia,
            categoria=self.categoria,
            codigo_barra=codigo_barra,
            nombre=nombre,
            precio=precio,
            existencia=99,
            existencia_minima=existencia_minima,
        )

    def test_producto_inicia_con_existencia_cero(self):
        producto = self.crear_producto("P-001", "Hemograma")

        self.assertEqual(producto.existencia, 0)
        self.assertTrue(producto.agotado)
        self.assertEqual(producto.estado_inventario, "agotado")

    def test_listado_resumen_agotados_y_bajo_stock(self):
        agotado = self.crear_producto("P-001", "Hemograma")
        bajo = self.crear_producto("P-002", "Glucosa", existencia_minima=2)
        ok = self.crear_producto("P-003", "Perfil lipidico", existencia_minima=2)
        MovimientoInventario.objects.create(
            empresa=self.empresa,
            producto=bajo,
            tipo=MovimientoInventario.Tipo.AJUSTE,
            cantidad=1,
            usuario=self.usuario,
        )
        MovimientoInventario.objects.create(
            empresa=self.empresa,
            producto=ok,
            tipo=MovimientoInventario.Tipo.AJUSTE,
            cantidad=5,
            usuario=self.usuario,
        )

        productos_response = self.client.get(reverse("inventario-productos"))
        resumen_response = self.client.get(reverse("inventario-resumen"))
        agotados_response = self.client.get(reverse("inventario-productos-agotados"))
        bajo_response = self.client.get(reverse("inventario-productos-bajo-stock"))

        self.assertEqual(productos_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(productos_response.data), 3)
        self.assertEqual(resumen_response.data["total_productos"], 3)
        self.assertEqual(resumen_response.data["productos_agotados"], 1)
        self.assertEqual(resumen_response.data["productos_bajo_stock"], 1)
        self.assertEqual(agotados_response.data[0]["codigo_barra"], agotado.codigo_barra)
        self.assertEqual(bajo_response.data[0]["codigo_barra"], bajo.codigo_barra)

    def test_ajustar_existencia_por_codigo_barra(self):
        producto = self.crear_producto("P-001", "Hemograma")

        response = self.client.post(
            reverse("inventario-ajustar-existencia"),
            {
                "codigo_barra": producto.codigo_barra,
                "existencia_nueva": 7,
                "motivo": "Conteo fisico",
            },
            format="json",
        )

        producto.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(producto.existencia, 7)
        self.assertEqual(response.data["producto"]["existencia"], 7)
        self.assertEqual(response.data["movimiento"]["existencia_anterior"], 0)
        self.assertEqual(response.data["movimiento"]["existencia_nueva"], 7)

    def test_ajustar_existencia_a_cero(self):
        producto = self.crear_producto("P-001", "Hemograma")
        MovimientoInventario.objects.create(
            empresa=self.empresa,
            producto=producto,
            tipo=MovimientoInventario.Tipo.AJUSTE,
            cantidad=5,
            usuario=self.usuario,
        )

        response = self.client.post(
            reverse("inventario-ajustar-existencia"),
            {
                "codigo_barra": producto.codigo_barra,
                "existencia_nueva": 0,
                "motivo": "Conteo fisico",
            },
            format="json",
        )

        producto.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(producto.existencia, 0)
        self.assertEqual(response.data["producto"]["estado_inventario"], "agotado")
