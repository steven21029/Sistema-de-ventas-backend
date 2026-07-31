from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from empresas.models import Empresa
from .datos.descripciones_examenes import DESCRIPCIONES_EXAMENES
from .models import Categoria, Familia, PaqueteCatalogo, PaqueteProducto, Producto
from .serializers import ProductoSerializer


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
        self.assertEqual(response.data[0]["cantidad_categorias"], 1)
        self.assertEqual(response.data[0]["cantidad_productos"], 1)
        self.assertEqual(response.data[0]["categorias"][0]["nombre"], self.categoria.nombre)

    def test_empresa_sin_imagenes_de_producto_usa_imagenes_de_clasificacion(self):
        self.empresa.productos_con_imagen = False
        self.empresa.save(
            update_fields=["productos_con_imagen", "fecha_actualizacion"]
        )
        self.categoria.imagen_url = "https://example.com/hematologia.jpg"
        self.categoria.save(update_fields=["imagen_url", "fecha_actualizacion"])

        examenes = self.client.get(
            reverse("catalogo-examenes"),
            {"empresa_slug": self.empresa.slug},
        )
        servicios = self.client.get(
            reverse("catalogo-servicios"),
            {"empresa_slug": self.empresa.slug},
        )

        self.assertEqual(examenes.status_code, status.HTTP_200_OK)
        self.assertIsNone(examenes.data[0]["imagen_final"])
        self.assertEqual(servicios.status_code, status.HTTP_200_OK)
        self.assertEqual(servicios.data[0]["imagen_final"], self.familia.imagen_url)
        self.assertEqual(
            servicios.data[0]["categorias"][0]["imagen_final"],
            self.categoria.imagen_url,
        )

    def test_detalle_servicio_publico_devuelve_categorias_y_productos(self):
        response = self.client.get(
            reverse("catalogo-servicio-detalle"),
            {
                "empresa_slug": self.empresa.slug,
                "servicio": "examenes",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["nombre"], self.familia.nombre)
        self.assertEqual(response.data["categorias"][0]["nombre"], self.categoria.nombre)
        self.assertEqual(
            response.data["categorias"][0]["productos"][0]["codigo_barra"],
            self.producto.codigo_barra,
        )
        self.assertNotIn("id", response.data["categorias"][0]["productos"][0])

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


class DescripcionesExamenesTests(APITestCase):
    def test_catalogo_contiene_328_descripciones_de_seis_palabras(self):
        self.assertEqual(len(DESCRIPCIONES_EXAMENES), 328)

        cantidades = {
            codigo: len(descripcion.split())
            for codigo, descripcion in DESCRIPCIONES_EXAMENES.items()
        }

        self.assertTrue(
            all(cantidad == 6 for cantidad in cantidades.values()),
            cantidades,
        )


class TipoItemCatalogoTests(APITestCase):
    def crear_clasificacion(self, empresa):
        familia = Familia.objects.create(
            empresa=empresa,
            nombre=f"Familia {empresa.slug}",
        )
        categoria = Categoria.objects.create(
            empresa=empresa,
            familia=familia,
            nombre=f"Categoria {empresa.slug}",
        )
        return familia, categoria

    def test_empresa_sin_inventario_crea_servicio_sin_codigo_barra(self):
        empresa = Empresa.objects.create(
            nombre="Empresa de servicios",
            slug="servicios",
            modo_inventario=Empresa.ModoInventario.SIN_INVENTARIO,
        )
        familia, categoria = self.crear_clasificacion(empresa)

        serializer = ProductoSerializer(
            data={
                "empresa": empresa.pk,
                "familia": familia.pk,
                "categoria": categoria.pk,
                "nombre": "Consulta",
                "precio": "500.00",
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        servicio = serializer.save()

        self.assertEqual(servicio.tipo_item, Producto.TipoItem.SERVICIO)
        self.assertIsNone(servicio.codigo_barra)
        self.assertTrue(servicio.codigo_interno.startswith("SRV-"))
        self.assertFalse(servicio.controla_inventario)
        self.assertFalse(servicio.agotado)
        self.assertEqual(servicio.estado_inventario, "no_aplica")

    def test_empresa_mixta_exige_tipo_item_en_api(self):
        empresa = Empresa.objects.create(
            nombre="Empresa mixta",
            slug="mixta",
            modo_inventario=Empresa.ModoInventario.MIXTO,
        )
        familia, categoria = self.crear_clasificacion(empresa)

        serializer = ProductoSerializer(
            data={
                "empresa": empresa.pk,
                "familia": familia.pk,
                "categoria": categoria.pk,
                "nombre": "Elemento sin tipo",
                "precio": "100.00",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("tipo_item", serializer.errors)

    def test_empresa_sin_imagenes_rechaza_imagen_individual_de_producto(self):
        empresa = Empresa.objects.create(
            nombre="Empresa sin imagenes de producto",
            slug="sin-imagenes-producto",
            modo_inventario=Empresa.ModoInventario.SIN_INVENTARIO,
            productos_con_imagen=False,
        )
        familia, categoria = self.crear_clasificacion(empresa)

        serializer = ProductoSerializer(
            data={
                "empresa": empresa.pk,
                "familia": familia.pk,
                "categoria": categoria.pk,
                "nombre": "Servicio con imagen",
                "precio": "100.00",
                "imagen_url": "https://example.com/servicio.jpg",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("imagen_principal", serializer.errors)

        with self.assertRaises(ValidationError):
            Producto.objects.create(
                empresa=empresa,
                familia=familia,
                categoria=categoria,
                nombre="Servicio creado internamente",
                precio="100.00",
                imagen_url="https://example.com/servicio-interno.jpg",
            )

    def test_empresa_mixta_permite_servicio_y_producto_fisico(self):
        empresa = Empresa.objects.create(
            nombre="Empresa mixta completa",
            slug="mixta-completa",
            modo_inventario=Empresa.ModoInventario.MIXTO,
        )
        familia, categoria = self.crear_clasificacion(empresa)

        servicio = Producto.objects.create(
            empresa=empresa,
            familia=familia,
            categoria=categoria,
            tipo_item=Producto.TipoItem.SERVICIO,
            nombre="Servicio",
            precio="100.00",
        )
        fisico = Producto.objects.create(
            empresa=empresa,
            familia=familia,
            categoria=categoria,
            tipo_item=Producto.TipoItem.PRODUCTO_FISICO,
            codigo_barra="FISICO-001",
            nombre="Producto fisico",
            precio="200.00",
        )

        self.assertFalse(servicio.controla_inventario)
        self.assertTrue(fisico.controla_inventario)
