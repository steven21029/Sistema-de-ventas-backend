from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from catalogo.models import Categoria, Familia, Producto
from empresas.models import Empresa
from usuarios.models import PerfilUsuario


User = get_user_model()


class PromocionesAdministrativasAPITests(APITestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Empresa promociones admin",
            slug="empresa-promociones-admin",
            modo_inventario=Empresa.ModoInventario.INVENTARIADO,
        )
        self.otra_empresa = Empresa.objects.create(
            nombre="Otra empresa promociones admin",
            slug="otra-promociones-admin",
            modo_inventario=Empresa.ModoInventario.INVENTARIADO,
        )
        self.producto = self._crear_producto(self.empresa, "PROMO-001")
        self.otro_producto = self._crear_producto(self.otra_empresa, "OTRA-001")
        self.admin = self._crear_usuario(
            "admin-promociones",
            PerfilUsuario.Rol.ADMINISTRADOR_EMPRESA,
            self.empresa,
        )
        self.comprador = self._crear_usuario(
            "comprador-promociones",
            PerfilUsuario.Rol.COMPRADOR,
            self.empresa,
        )
        self.maestro = self._crear_usuario(
            "maestro-promociones",
            PerfilUsuario.Rol.ADMINISTRADOR_MAESTRO,
            None,
        )
        self.maestro.perfil.empresas_permitidas.add(self.empresa)

    def _crear_producto(self, empresa, codigo):
        familia = Familia.objects.create(
            empresa=empresa,
            nombre=f"Familia {codigo}",
        )
        categoria = Categoria.objects.create(
            empresa=empresa,
            familia=familia,
            nombre=f"Categoria {codigo}",
        )
        return Producto.objects.create(
            empresa=empresa,
            familia=familia,
            categoria=categoria,
            codigo_barra=codigo,
            nombre=f"Producto {codigo}",
            precio=Decimal("100.00"),
        )

    def _crear_usuario(self, username, rol, empresa):
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="Prueba12345!",
        )
        perfil = user.perfil
        perfil.rol = rol
        perfil.empresa = empresa
        perfil.activo = True
        perfil.correo_verificado = True
        perfil.save()
        return user

    def test_admin_crea_oferta_con_productos_ids(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            reverse("promociones-ofertas-list"),
            {
                "tipo": "producto",
                "codigo": "OFERTA-ADMIN",
                "titulo": "Oferta administrativa",
                "precio_normal": "100.00",
                "precio_oferta": "80.00",
                "porcentaje_descuento": 20,
                "productos_ids": [self.producto.id],
                "activo": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["empresa"], self.empresa.id)
        self.assertEqual(response.data["productos"][0]["codigo"], "PROMO-001")

    def test_oferta_rechaza_producto_de_otra_empresa(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            reverse("promociones-ofertas-list"),
            {
                "tipo": "producto",
                "codigo": "OFERTA-CRUZADA",
                "titulo": "Oferta cruzada",
                "precio_normal": "100.00",
                "precio_oferta": "80.00",
                "productos_ids": [self.otro_producto.id],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("productos_ids", response.data)

    def test_panel_puede_solicitar_paginacion(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(
            reverse("promociones-ofertas-list"),
            {"incluir_inactivos": "true", "paginar": "true"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)

    def test_comprador_autenticado_debe_enviar_slug_publico(self):
        self.client.force_authenticate(self.comprador)
        response = self.client.get(reverse("promociones-ofertas-list"))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("empresa_slug", response.data)

    def test_maestro_recibe_403_para_empresa_no_permitida(self):
        self.client.force_authenticate(self.maestro)
        response = self.client.get(
            reverse("promociones-banners-list"),
            {"empresa_slug": self.otra_empresa.slug},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
