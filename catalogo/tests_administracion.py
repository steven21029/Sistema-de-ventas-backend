from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from empresas.models import Empresa
from usuarios.models import PerfilUsuario

from .models import Categoria, Familia, PaqueteCatalogo, PaqueteProducto, Producto


User = get_user_model()


class CatalogoAdministrativoAPITests(APITestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Empresa catalogo",
            slug="empresa-catalogo",
            modo_inventario=Empresa.ModoInventario.INVENTARIADO,
        )
        self.otra_empresa = Empresa.objects.create(
            nombre="Otra empresa catalogo",
            slug="otra-empresa-catalogo",
            modo_inventario=Empresa.ModoInventario.INVENTARIADO,
        )
        self.familia = Familia.objects.create(
            empresa=self.empresa,
            nombre="Familia principal",
        )
        self.categoria = Categoria.objects.create(
            empresa=self.empresa,
            familia=self.familia,
            nombre="Categoria principal",
        )
        self.producto = Producto.objects.create(
            empresa=self.empresa,
            familia=self.familia,
            categoria=self.categoria,
            codigo_barra="CAT-001",
            nombre="Producto principal",
            precio=Decimal("100.00"),
        )
        self.otra_familia = Familia.objects.create(
            empresa=self.otra_empresa,
            nombre="Familia externa",
        )
        self.otra_categoria = Categoria.objects.create(
            empresa=self.otra_empresa,
            familia=self.otra_familia,
            nombre="Categoria externa",
        )
        self.otro_producto = Producto.objects.create(
            empresa=self.otra_empresa,
            familia=self.otra_familia,
            categoria=self.otra_categoria,
            codigo_barra="EXT-001",
            nombre="Producto externo",
            precio=Decimal("80.00"),
        )
        self.admin = self._crear_usuario(
            "admin-catalogo",
            PerfilUsuario.Rol.ADMINISTRADOR_EMPRESA,
        )
        self.comprador = self._crear_usuario(
            "comprador-catalogo",
            PerfilUsuario.Rol.COMPRADOR,
        )

    def _crear_usuario(self, username, rol):
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="Prueba12345!",
        )
        perfil = user.perfil
        perfil.empresa = self.empresa
        perfil.rol = rol
        perfil.activo = True
        perfil.correo_verificado = True
        perfil.save()
        return user

    def test_producto_administrativo_incluye_id_y_actualiza_orden(self):
        self.client.force_authenticate(self.admin)
        listado = self.client.get(reverse("catalogo-productos-list"))

        self.assertEqual(listado.status_code, status.HTTP_200_OK)
        self.assertIn("results", listado.data)
        self.assertEqual(listado.data["results"][0]["id"], self.producto.id)

        actualizada = self.client.patch(
            reverse("catalogo-productos-detail", args=[self.producto.id]),
            {"orden": 7},
            format="json",
        )
        self.assertEqual(actualizada.status_code, status.HTTP_200_OK)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.orden_destacado, 7)

    def test_categoria_rechaza_familia_de_otra_empresa(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            reverse("catalogo-categorias-list"),
            {
                "empresa": self.otra_empresa.id,
                "familia": self.otra_familia.id,
                "nombre": "Categoria cruzada",
                "orden": 20,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("familia", response.data)

    def test_crud_paquete_guarda_cantidad_por_producto(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            reverse("catalogo-paquetes-list"),
            {
                "tipo": "combo",
                "codigo": "COMBO-001",
                "nombre": "Combo de prueba",
                "descripcion": "Paquete administrativo",
                "precio_normal": "200.00",
                "precio": "150.00",
                "porcentaje_descuento": 25,
                "activo": True,
                "productos": [
                    {
                        "producto_id": self.producto.id,
                        "cantidad": 2,
                        "orden": 1,
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        paquete = PaqueteCatalogo.objects.get(pk=response.data["id"])
        item = paquete.items_productos.get()
        self.assertEqual(item.cantidad, 2)
        self.assertEqual(response.data["productos_detalle"][0]["cantidad"], 2)

        actualizado = self.client.patch(
            reverse("catalogo-paquetes-detail", args=[paquete.id]),
            {"productos": [{"producto_id": self.producto.id, "cantidad": 3}]},
            format="json",
        )
        self.assertEqual(actualizado.status_code, status.HTTP_200_OK)
        item = paquete.items_productos.get()
        self.assertEqual(item.cantidad, 3)

    def test_paquete_rechaza_producto_de_otra_empresa(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            reverse("catalogo-paquetes-list"),
            {
                "tipo": "perfil",
                "codigo": "PERFIL-EXT",
                "nombre": "Perfil invalido",
                "precio_normal": "100.00",
                "precio": "90.00",
                "activo": True,
                "productos": [
                    {"producto_id": self.otro_producto.id, "cantidad": 1}
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("productos", response.data)

    def test_comprador_no_accede_al_crud_de_paquetes(self):
        self.client.force_authenticate(self.comprador)
        response = self.client.get(reverse("catalogo-paquetes-list"))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_recibe_403_al_solicitar_catalogo_de_otra_empresa(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(
            reverse("catalogo-productos-list"),
            {"empresa_slug": self.otra_empresa.slug},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_producto_con_paquete_responde_409_al_eliminar(self):
        paquete = PaqueteCatalogo.objects.create(
            empresa=self.empresa,
            tipo=PaqueteCatalogo.Tipo.COMBO,
            codigo="COMBO-PROTEGIDO",
            nombre="Combo protegido",
            precio_normal=Decimal("100.00"),
            precio_paquete=Decimal("90.00"),
        )
        PaqueteProducto.objects.create(
            paquete=paquete,
            producto=self.producto,
            cantidad=1,
        )
        self.client.force_authenticate(self.admin)

        response = self.client.delete(
            reverse("catalogo-productos-detail", args=[self.producto.id])
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_paquete_agotado_considera_cantidad_del_componente(self):
        self.producto.existencia = 1
        self.producto.save(update_fields=["existencia", "fecha_actualizacion"])
        paquete = PaqueteCatalogo.objects.create(
            empresa=self.empresa,
            tipo=PaqueteCatalogo.Tipo.COMBO,
            codigo="COMBO-AGOTADO",
            nombre="Combo agotado",
            precio_normal=Decimal("100.00"),
            precio_paquete=Decimal("90.00"),
        )
        PaqueteProducto.objects.create(
            paquete=paquete,
            producto=self.producto,
            cantidad=2,
        )

        self.assertTrue(paquete.agotado)
