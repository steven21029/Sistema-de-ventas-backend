from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from catalogo.models import (
    Categoria,
    Familia,
    PaqueteCatalogo,
    PaqueteProducto,
    Producto,
)
from empresas.models import Empresa
from usuarios.models import PerfilUsuario
from .models import Favorito


class FavoritosServiciosTests(APITestCase):
    def test_servicio_se_agrega_por_codigo_interno(self):
        empresa = Empresa.objects.create(
            nombre="Servicios favoritos",
            slug="servicios-favoritos",
            modo_inventario=Empresa.ModoInventario.SIN_INVENTARIO,
        )
        familia = Familia.objects.create(empresa=empresa, nombre="Servicios")
        categoria = Categoria.objects.create(
            empresa=empresa,
            familia=familia,
            nombre="Consultas",
        )
        servicio = Producto.objects.create(
            empresa=empresa,
            familia=familia,
            categoria=categoria,
            nombre="Consulta general",
            precio="400.00",
        )
        usuario = get_user_model().objects.create_user(
            username="favorito@example.com",
            email="favorito@example.com",
            password="ClaveSegura123!",
        )
        usuario.perfil.empresa = empresa
        usuario.perfil.rol = PerfilUsuario.Rol.COMPRADOR
        usuario.perfil.activo = True
        usuario.perfil.correo_verificado = True
        usuario.perfil.save()
        self.client.force_authenticate(usuario)

        response = self.client.post(
            "/api/favoritos/",
            {"codigo": servicio.codigo_interno},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["producto_codigo"], servicio.codigo_interno)
        self.assertEqual(response.data["producto_tipo_item"], "servicio")
        self.assertFalse(response.data["producto_controla_inventario"])
        self.assertEqual(response.data["tipo_articulo"], "producto")
        self.assertEqual(response.data["articulo_nombre"], servicio.nombre)
        self.assertEqual(response.data["articulo_precio"], "400.00")


class FavoritosPaquetesTests(APITestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Catalogo favorito completo",
            slug="catalogo-favorito-completo",
            modo_inventario=Empresa.ModoInventario.SIN_INVENTARIO,
        )
        self.familia = Familia.objects.create(
            empresa=self.empresa,
            nombre="Examenes",
        )
        self.categoria = Categoria.objects.create(
            empresa=self.empresa,
            familia=self.familia,
            nombre="Laboratorio",
        )
        self.producto = Producto.objects.create(
            empresa=self.empresa,
            familia=self.familia,
            categoria=self.categoria,
            nombre="Hemograma",
            precio="300.00",
        )
        self.perfil = PaqueteCatalogo.objects.create(
            empresa=self.empresa,
            tipo=PaqueteCatalogo.Tipo.PERFIL,
            codigo="PERFIL-001",
            nombre="Perfil preventivo",
            descripcion="Evaluacion preventiva",
            precio_normal="600.00",
            precio_paquete="500.00",
            imagen_url="https://example.com/perfil.jpg",
        )
        self.combo = PaqueteCatalogo.objects.create(
            empresa=self.empresa,
            tipo=PaqueteCatalogo.Tipo.COMBO,
            codigo="COMBO-001",
            nombre="Combo anual",
            descripcion="Evaluacion anual",
            precio_normal="800.00",
            precio_paquete="650.00",
        )
        PaqueteProducto.objects.create(
            paquete=self.perfil,
            producto=self.producto,
        )
        PaqueteProducto.objects.create(
            paquete=self.combo,
            producto=self.producto,
        )
        self.usuario = self.crear_usuario("cliente1@example.com")
        self.otro_usuario = self.crear_usuario("cliente2@example.com")
        self.client.force_authenticate(self.usuario)

    def crear_usuario(self, email):
        usuario = get_user_model().objects.create_user(
            username=email,
            email=email,
            password="ClaveSegura123!",
        )
        usuario.perfil.empresa = self.empresa
        usuario.perfil.rol = PerfilUsuario.Rol.COMPRADOR
        usuario.perfil.activo = True
        usuario.perfil.correo_verificado = True
        usuario.perfil.save()
        return usuario

    def test_perfil_se_guarda_y_devuelve_con_campos_unificados(self):
        self.empresa.productos_con_imagen = False
        self.empresa.save(
            update_fields=["productos_con_imagen", "fecha_actualizacion"]
        )

        response = self.client.post(
            "/api/favoritos/",
            {
                "codigo": self.perfil.codigo,
                "tipo_articulo": "perfil",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["tipo_articulo"], "perfil")
        self.assertEqual(response.data["articulo_codigo"], self.perfil.codigo)
        self.assertEqual(response.data["articulo_nombre"], self.perfil.nombre)
        self.assertEqual(response.data["articulo_precio"], "500.00")
        self.assertEqual(
            response.data["articulo_imagen_final"],
            self.perfil.imagen_url,
        )

    def test_producto_respeta_configuracion_de_imagenes_de_empresa(self):
        self.producto.imagen_url = "https://example.com/producto.jpg"
        self.producto.save()
        self.empresa.productos_con_imagen = False
        self.empresa.save(
            update_fields=["productos_con_imagen", "fecha_actualizacion"]
        )

        response = self.client.post(
            "/api/favoritos/",
            {
                "codigo": self.producto.codigo_interno,
                "tipo_articulo": "producto",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data["articulo_imagen_final"])
        self.assertIsNone(response.data["producto_imagen_principal"])

    def test_combo_favorito_no_se_duplica(self):
        datos = {
            "codigo": self.combo.codigo,
            "tipo_articulo": "combo",
        }

        primera = self.client.post("/api/favoritos/", datos, format="json")
        segunda = self.client.post("/api/favoritos/", datos, format="json")

        self.assertEqual(primera.status_code, status.HTTP_201_CREATED)
        self.assertEqual(segunda.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            Favorito.objects.filter(
                empresa=self.empresa,
                usuario=self.usuario,
                paquete=self.combo,
            ).count(),
            1,
        )

    def test_listado_persiste_y_separa_favoritos_por_cliente(self):
        Favorito.objects.create(
            empresa=self.empresa,
            usuario=self.usuario,
            paquete=self.perfil,
        )
        Favorito.objects.create(
            empresa=self.empresa,
            usuario=self.otro_usuario,
            paquete=self.combo,
        )

        response = self.client.get(
            "/api/favoritos/",
            {"empresa_slug": self.empresa.slug},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["articulo_codigo"], self.perfil.codigo)

    def test_codigo_ambiguo_exige_tipo_articulo(self):
        Producto.objects.create(
            empresa=self.empresa,
            familia=self.familia,
            categoria=self.categoria,
            codigo_barra=self.perfil.codigo,
            nombre="Servicio con codigo repetido entre tipos",
            precio="200.00",
        )

        response = self.client.post(
            "/api/favoritos/",
            {"codigo": self.perfil.codigo},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("tipo_articulo", response.data)
