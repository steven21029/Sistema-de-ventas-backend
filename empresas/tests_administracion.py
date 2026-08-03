from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from usuarios.models import PerfilUsuario

from .models import Empresa, ItemMenuEmpresa, SobreNosotrosEmpresa, SucursalEmpresa


User = get_user_model()


class ContextoAdministrativoAPITests(APITestCase):
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
        self.superuser = User.objects.create_superuser(
            username="root",
            email="root@example.com",
            password="Prueba12345!",
        )
        self.admin_empresa = self._crear_usuario(
            "admin-analiza",
            PerfilUsuario.Rol.ADMINISTRADOR_EMPRESA,
            self.analiza,
        )
        self.gerente = self._crear_usuario(
            "gerente-analiza",
            PerfilUsuario.Rol.GERENTE,
            self.analiza,
        )
        self.comprador = self._crear_usuario(
            "comprador-analiza",
            PerfilUsuario.Rol.COMPRADOR,
            self.analiza,
        )
        self.maestro = self._crear_usuario(
            "maestro",
            PerfilUsuario.Rol.ADMINISTRADOR_MAESTRO,
            None,
        )
        self.maestro.perfil.empresas_permitidas.add(self.analiza)

    def _crear_usuario(self, username, rol, empresa):
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="Prueba12345!",
        )
        perfil = user.perfil
        perfil.rol = rol
        perfil.empresa = empresa
        perfil.correo_verificado = True
        perfil.activo = True
        perfil.save()
        return user

    def test_superusuario_resuelve_empresa_por_subdominio(self):
        self.client.force_authenticate(self.superuser)
        response = self.client.get(
            reverse("empresas-contexto-administrativo"),
            HTTP_X_FRONTEND_HOST="analiza.localhost",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["empresa_actual"]["slug"], "analiza")
        self.assertEqual(len(response.data["empresas_disponibles"]), 2)

    def test_administrador_empresa_administra_solo_su_empresa(self):
        self.client.force_authenticate(self.admin_empresa)
        response = self.client.patch(
            reverse("empresas-mi-empresa"),
            {"telefono": "2222-3333", "slug": "slug-no-permitido"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.analiza.refresh_from_db()
        self.assertEqual(self.analiza.telefono, "2222-3333")
        self.assertEqual(self.analiza.slug, "analiza")

        response = self.client.get(
            reverse("empresas-mi-empresa"),
            HTTP_X_FRONTEND_HOST="otra.localhost",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_administrador_actualiza_redes_sociales_de_su_empresa(self):
        self.client.force_authenticate(self.admin_empresa)
        response = self.client.patch(
            reverse("empresas-mi-empresa"),
            {
                "instagram_url": "https://www.instagram.com/analiza",
                "whatsapp_url": "https://wa.me/50499999999",
                "facebook_url": "https://www.facebook.com/analiza",
                "tiktok_url": "https://www.tiktok.com/@analiza",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.analiza.refresh_from_db()
        self.assertEqual(
            self.analiza.instagram_url,
            "https://www.instagram.com/analiza",
        )
        self.assertEqual(self.analiza.whatsapp_url, "https://wa.me/50499999999")

    def test_red_social_rechaza_dominio_incorrecto(self):
        self.client.force_authenticate(self.admin_empresa)
        response = self.client.patch(
            reverse("empresas-mi-empresa"),
            {"instagram_url": "https://example.com/analiza"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("instagram_url", response.data)

    def test_red_social_rechaza_url_sin_https(self):
        self.client.force_authenticate(self.admin_empresa)
        response = self.client.patch(
            reverse("empresas-mi-empresa"),
            {"instagram_url": "http://www.instagram.com/analiza"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("instagram_url", response.data)

    def test_gerente_puede_consultar_su_empresa(self):
        self.client.force_authenticate(self.gerente)
        response = self.client.get(reverse("empresas-mi-empresa"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["slug"], "analiza")

    def test_maestro_solo_accede_a_empresas_permitidas(self):
        self.client.force_authenticate(self.maestro)
        permitida = self.client.get(
            reverse("empresas-mi-empresa"),
            {"empresa_slug": "analiza"},
        )
        denegada = self.client.get(
            reverse("empresas-mi-empresa"),
            {"empresa_slug": "otra"},
        )

        self.assertEqual(permitida.status_code, status.HTTP_200_OK)
        self.assertEqual(denegada.status_code, status.HTTP_403_FORBIDDEN)

    def test_comprador_no_tiene_acceso_administrativo(self):
        self.client.force_authenticate(self.comprador)
        response = self.client.get(reverse("empresas-mi-empresa"))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_sin_autenticacion_recibe_401(self):
        response = self.client.get(reverse("empresas-mi-empresa"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ContenidoEmpresaAdministrativoAPITests(ContextoAdministrativoAPITests):
    def test_admin_no_puede_crear_items_de_menu(self):
        self.client.force_authenticate(self.admin_empresa)
        response = self.client.post(
            reverse("empresas-items-menu-list"),
            {
                "empresa": self.otra.id,
                "clave": "novedades",
                "texto": "Novedades",
                "ruta": "/novedades",
                "orden": 20,
                "activo": True,
                "abre_en_nueva_pestana": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertFalse(ItemMenuEmpresa.objects.filter(clave="novedades").exists())

    def test_menu_rechaza_orden_duplicado(self):
        self.client.force_authenticate(self.admin_empresa)
        item = self.analiza.items_menu.get(clave="sobre_nosotros")
        response = self.client.patch(
            reverse("empresas-items-menu-detail", args=[item.pk]),
            {"orden": 1},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("orden", response.data)

    def test_admin_solo_cambia_texto_orden_y_estado_del_menu(self):
        item = self.analiza.items_menu.get(clave="sobre_nosotros")
        self.client.force_authenticate(self.admin_empresa)
        response = self.client.patch(
            reverse("empresas-items-menu-detail", args=[item.pk]),
            {
                "clave": "servicios",
                "ruta": "/ruta-inventada",
                "abre_en_nueva_pestana": True,
                "texto": "Acerca de nosotros",
                "orden": 20,
                "activo": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item.refresh_from_db()
        self.assertEqual(item.clave, "sobre_nosotros")
        self.assertEqual(item.ruta, "/sobre-nosotros")
        self.assertFalse(item.abre_en_nueva_pestana)
        self.assertEqual(item.texto, "Acerca de nosotros")
        self.assertEqual(item.orden, 20)
        self.assertFalse(item.activo)

    def test_admin_no_puede_eliminar_item_menu(self):
        item = self.analiza.items_menu.get(clave="sobre_nosotros")
        self.client.force_authenticate(self.admin_empresa)
        response = self.client.delete(
            reverse("empresas-items-menu-detail", args=[item.pk])
        )

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertTrue(ItemMenuEmpresa.objects.filter(pk=item.pk).exists())

    def test_comprador_no_puede_modificar_menu(self):
        item = self.analiza.items_menu.get(clave="sobre_nosotros")
        self.client.force_authenticate(self.comprador)
        response = self.client.patch(
            reverse("empresas-items-menu-detail", args=[item.pk]),
            {"texto": "Privado"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_actualiza_sobre_nosotros_de_su_empresa(self):
        self.client.force_authenticate(self.admin_empresa)
        response = self.client.patch(
            reverse("empresas-mi-sobre-nosotros"),
            {
                "titulo": "Sobre Analiza",
                "mision": "Brindar resultados confiables.",
                "vision": "Ser referentes nacionales.",
                "valores": "Calidad\nEtica",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        contenido = SobreNosotrosEmpresa.objects.get(empresa=self.analiza)
        self.assertEqual(contenido.titulo, "Sobre Analiza")
        self.assertEqual(response.data["valores_lista"], ["Calidad", "Etica"])

    def test_admin_no_actualiza_sobre_nosotros_de_otra_empresa(self):
        self.client.force_authenticate(self.admin_empresa)
        response = self.client.patch(
            reverse("empresas-mi-sobre-nosotros"),
            {"titulo": "Contenido externo"},
            format="json",
            HTTP_X_FRONTEND_HOST="otra.localhost",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertNotEqual(self.otra.sobre_nosotros.titulo, "Contenido externo")

    def test_comprador_no_accede_a_edicion_sobre_nosotros(self):
        self.client.force_authenticate(self.comprador)
        response = self.client.get(reverse("empresas-mi-sobre-nosotros"))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_sucursales_publicas_conservan_lista_sin_paginar(self):
        SucursalEmpresa.objects.create(
            empresa=self.analiza,
            nombre="Principal",
            direccion="Centro",
        )
        SucursalEmpresa.objects.create(
            empresa=self.analiza,
            nombre="Oculta",
            direccion="Centro",
            activa=False,
        )

        response = self.client.get(
            reverse("empresas-sucursales"),
            {"empresa_slug": "analiza"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 1)
        self.assertNotIn("id", response.data[0])

    def test_admin_gestiona_sucursales_con_paginacion(self):
        self.client.force_authenticate(self.admin_empresa)
        creada = self.client.post(
            reverse("empresas-sucursales"),
            {
                "nombre": "Sucursal Norte",
                "direccion": "Colonia Norte",
                "latitud": "14.083697123456789",
                "longitud": "-87.206811987654321",
                "activa": False,
            },
            format="json",
        )

        self.assertEqual(creada.status_code, status.HTTP_201_CREATED)
        listado = self.client.get(
            reverse("empresas-sucursales"),
            {"incluir_inactivos": "true"},
        )
        self.assertEqual(listado.status_code, status.HTTP_200_OK)
        self.assertIn("results", listado.data)
        self.assertEqual(listado.data["results"][0]["id"], creada.data["id"])

        actualizada = self.client.patch(
            reverse("empresas-sucursales-detalle", args=[creada.data["id"]]),
            {"activa": True},
            format="json",
        )
        self.assertEqual(actualizada.status_code, status.HTTP_200_OK)
        self.assertTrue(actualizada.data["activa"])
