from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import (
    Departamento,
    Empresa,
    ItemMenuEmpresa,
    Municipio,
    SobreNosotrosEmpresa,
    SucursalEmpresa,
)


class EmpresaActualAPITests(APITestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Analiza Laboratorios Clinicos",
            slug="Analiza",
            subdominio="analiza",
            dominio_personalizado="tienda.analizahn.com",
        )
        self.departamento = Departamento.objects.get(codigo="08")
        self.municipio = Municipio.objects.get(codigo="0801")

    def test_resuelve_empresa_por_subdominio_localhost(self):
        response = self.client.get(
            reverse("empresas-actual"),
            {"host": "analiza.localhost:3000"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["slug"], self.empresa.slug)
        self.assertEqual(response.data["subdominio"], "analiza")
        self.assertEqual(len(response.data["menu"]), 8)
        self.assertFalse(response.data["pago_en_linea_disponible"])

    def test_resuelve_empresa_por_dominio_personalizado(self):
        response = self.client.get(
            reverse("empresas-actual"),
            {"host": "https://tienda.analizahn.com:443/inicio"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["slug"], self.empresa.slug)
        self.assertEqual(
            response.data["dominio_personalizado"],
            "tienda.analizahn.com",
        )

    def test_resuelve_empresa_por_slug_como_respaldo(self):
        response = self.client.get(
            reverse("empresas-actual"),
            {"slug": self.empresa.slug},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["slug"], self.empresa.slug)

    def test_no_resuelve_empresa_inactiva(self):
        self.empresa.activa = False
        self.empresa.save(update_fields=["activa"])

        response = self.client.get(
            reverse("empresas-actual"),
            {"host": "analiza.localhost:3000"},
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_menu_endpoint_devuelve_menu_configurable_por_empresa(self):
        item = self.empresa.items_menu.get(clave="examenes")
        item.texto = "Productos"
        item.ruta = "/productos"
        item.save(update_fields=["texto", "ruta", "fecha_actualizacion"])
        self.empresa.items_menu.filter(clave="sucursales").update(activo=False)

        response = self.client.get(
            reverse("empresas-menu"),
            {"empresa_slug": self.empresa.slug},
        )

        textos = [item["texto"] for item in response.data]
        rutas = {item["clave"]: item["ruta"] for item in response.data}
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Productos", textos)
        self.assertNotIn("Sucursales", textos)
        self.assertEqual(rutas["examenes"], "/examenes")

    def test_empresa_nueva_recibe_solo_modulos_oficiales_y_sobre_nosotros(self):
        claves = set(self.empresa.items_menu.values_list("clave", flat=True))

        self.assertEqual(
            claves,
            {
                "inicio",
                "examenes",
                "perfiles",
                "servicios",
                "promociones",
                "sucursales",
                "contacto",
                "sobre_nosotros",
            },
        )
        self.assertTrue(
            SobreNosotrosEmpresa.objects.filter(empresa=self.empresa).exists()
        )

    def test_modelo_rechaza_item_de_menu_no_oficial(self):
        with self.assertRaises(DjangoValidationError):
            ItemMenuEmpresa.objects.create(
                empresa=self.empresa,
                clave="pagina-libre",
                texto="Pagina libre",
                ruta="/pagina-libre",
            )

    def test_api_publica_devuelve_plantilla_sobre_nosotros(self):
        contenido = self.empresa.sobre_nosotros
        contenido.titulo = "Acerca de Analiza"
        contenido.introduccion = "Laboratorio clinico hondureno."
        contenido.mision = "Cuidar la salud con resultados confiables."
        contenido.vision = "Ser un laboratorio de referencia nacional."
        contenido.valores = "Calidad\nEtica\nServicio"
        contenido.imagen_url = "https://example.com/sobre-analiza.jpg"
        contenido.save()

        response = self.client.get(
            reverse("empresas-sobre-nosotros"),
            {"empresa_slug": self.empresa.slug},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["titulo"], "Acerca de Analiza")
        self.assertEqual(response.data["valores_lista"], ["Calidad", "Etica", "Servicio"])
        self.assertEqual(
            response.data["imagen_final"],
            "https://example.com/sobre-analiza.jpg",
        )
        self.assertNotIn("id", response.data)
        self.assertNotIn("empresa", response.data)

    def test_sobre_nosotros_inactivo_en_menu_no_es_publico(self):
        self.empresa.items_menu.filter(clave="sobre_nosotros").update(activo=False)

        response = self.client.get(
            reverse("empresas-sobre-nosotros"),
            {"empresa_slug": self.empresa.slug},
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_menu_endpoint_resuelve_por_host(self):
        response = self.client.get(
            reverse("empresas-menu"),
            {"host": "analiza.localhost:3000"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["clave"], "inicio")

    def test_sucursales_publicas_por_empresa_slug_y_busqueda(self):
        SucursalEmpresa.objects.create(
            empresa=self.empresa,
            nombre="Sucursal Centro",
            municipio=self.municipio,
            direccion="Centro comercial",
            telefono="22222222",
            horario=(
                "Lunes a viernes: 6:30am-5:00pm; "
                "Sabado: 6:30am-1:00pm; "
                "Domingo: Cerrado"
            ),
            google_maps_url="https://maps.google.com/example",
            imagen_url="https://example.com/sucursal-centro.jpg",
        )
        SucursalEmpresa.objects.create(
            empresa=self.empresa,
            nombre="Sucursal inactiva",
            direccion="No visible",
            activa=False,
        )

        response = self.client.get(
            reverse("empresas-sucursales"),
            {
                "empresa_slug": self.empresa.slug,
                "buscar": "centro",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["nombre"], "Sucursal Centro")
        self.assertEqual(response.data[0]["municipio_id"], self.municipio.pk)
        self.assertEqual(response.data[0]["municipio"], "Distrito Central")
        self.assertEqual(response.data[0]["departamento_id"], self.departamento.pk)
        self.assertEqual(response.data[0]["departamento"], "Francisco Morazan")
        self.assertEqual(response.data[0]["ciudad"], "Distrito Central")
        self.assertEqual(response.data[0]["estado"], SucursalEmpresa.Estado.ACTIVA)
        self.assertEqual(
            response.data[0]["horario_lineas"],
            [
                "Lunes a viernes: 6:30am-5:00pm",
                "Sabado: 6:30am-1:00pm",
                "Domingo: Cerrado",
            ],
        )
        self.assertIsNone(response.data[0]["imagen_final"])
        self.assertNotIn("imagen_url", response.data[0])
        self.assertEqual(
            response.data[0]["id"],
            SucursalEmpresa.objects.get(nombre="Sucursal Centro").pk,
        )

        por_municipio = self.client.get(
            reverse("empresas-sucursales"),
            {
                "empresa_slug": self.empresa.slug,
                "municipio": "distrito central",
            },
        )
        self.assertEqual(por_municipio.status_code, status.HTTP_200_OK)
        self.assertEqual(len(por_municipio.data), 1)

    def test_sucursales_usan_imagen_general_de_empresa(self):
        self.empresa.imagen_sucursales_url = "https://example.com/sucursales-general.jpg"
        self.empresa.save(update_fields=["imagen_sucursales_url", "fecha_actualizacion"])
        SucursalEmpresa.objects.create(
            empresa=self.empresa,
            nombre="Sucursal Centro",
            direccion="Centro comercial",
            imagen_url="https://example.com/sucursal-individual.jpg",
        )

        response = self.client.get(
            reverse("empresas-sucursales"),
            {"empresa_slug": self.empresa.slug},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data[0]["imagen_final"],
            "https://example.com/sucursales-general.jpg",
        )

    def test_empresa_publica_devuelve_imagen_general_de_sucursales(self):
        self.empresa.imagen_sucursales_url = "https://example.com/sucursales-general.jpg"
        self.empresa.save(update_fields=["imagen_sucursales_url", "fecha_actualizacion"])

        response = self.client.get(
            reverse("empresas-actual"),
            {"slug": self.empresa.slug},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["imagen_sucursales_final"],
            "https://example.com/sucursales-general.jpg",
        )

    def test_empresa_publica_devuelve_configuracion_de_inventario(self):
        self.empresa.modo_inventario = Empresa.ModoInventario.SIN_INVENTARIO
        self.empresa.save(update_fields=["modo_inventario", "fecha_actualizacion"])

        response = self.client.get(
            reverse("empresas-actual"),
            {"slug": self.empresa.slug},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["modo_inventario"], "sin_inventario")
        self.assertFalse(response.data["permite_productos_fisicos"])
        self.assertTrue(response.data["permite_servicios"])

    def test_empresa_publica_devuelve_configuracion_de_impuesto(self):
        self.empresa.cobra_impuesto = False
        self.empresa.save(update_fields=["cobra_impuesto", "fecha_actualizacion"])

        response = self.client.get(
            reverse("empresas-actual"),
            {"slug": self.empresa.slug},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["cobra_impuesto"])

    def test_empresa_publica_devuelve_configuracion_de_imagenes_de_producto(self):
        self.empresa.productos_con_imagen = False
        self.empresa.save(
            update_fields=["productos_con_imagen", "fecha_actualizacion"]
        )

        response = self.client.get(
            reverse("empresas-actual"),
            {"slug": self.empresa.slug},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["productos_con_imagen"])

    def test_empresa_publica_devuelve_una_sola_configuracion_de_redes_sociales(self):
        self.empresa.instagram_url = "https://www.instagram.com/analiza"
        self.empresa.whatsapp_url = "https://wa.me/50499999999"
        self.empresa.facebook_url = "https://www.facebook.com/analiza"
        self.empresa.tiktok_url = "https://www.tiktok.com/@analiza"
        self.empresa.save()

        response = self.client.get(
            reverse("empresas-actual"),
            {"slug": self.empresa.slug},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["redes_sociales"],
            {
                "instagram_url": "https://www.instagram.com/analiza",
                "whatsapp_url": "https://wa.me/50499999999",
                "facebook_url": "https://www.facebook.com/analiza",
                "tiktok_url": "https://www.tiktok.com/@analiza",
            },
        )
        self.assertNotIn("instagram_url", response.data)
        self.assertNotIn("whatsapp_url", response.data)

    def test_redes_sociales_publicas_estan_aisladas_por_empresa(self):
        self.empresa.instagram_url = "https://www.instagram.com/analiza"
        self.empresa.save()
        otra = Empresa.objects.create(
            nombre="Otra empresa",
            slug="otra-empresa",
            subdominio="otra-empresa",
        )

        response = self.client.get(
            reverse("empresas-publica"),
            {"slug": otra.slug},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["redes_sociales"],
            {
                "instagram_url": "",
                "whatsapp_url": "",
                "facebook_url": "",
                "tiktok_url": "",
            },
        )

    def test_sucursales_aceptan_coordenadas_largas(self):
        latitud = Decimal("14.083697123456789")
        longitud = Decimal("-87.206811987654321")
        precision_practica = Decimal("0.000000000001")
        SucursalEmpresa.objects.create(
            empresa=self.empresa,
            nombre="Sucursal Coordenadas",
            direccion="Direccion con ubicacion exacta",
            latitud=latitud,
            longitud=longitud,
        )

        response = self.client.get(
            reverse("empresas-sucursales"),
            {"empresa_slug": self.empresa.slug},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            Decimal(response.data[0]["latitud"]).quantize(precision_practica),
            latitud.quantize(precision_practica),
        )
        self.assertEqual(
            Decimal(response.data[0]["longitud"]).quantize(precision_practica),
            longitud.quantize(precision_practica),
        )
