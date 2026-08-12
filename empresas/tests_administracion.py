from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from usuarios.models import PerfilUsuario

from .models import (
    Departamento,
    Empresa,
    ItemMenuEmpresa,
    Municipio,
    SobreNosotrosEmpresa,
    SucursalEmpresa,
)


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
        self.departamento = Departamento.objects.get(codigo="08")
        self.departamento_cortes = Departamento.objects.get(codigo="05")
        self.municipio = Municipio.objects.get(codigo="0801")
        self.choloma = Municipio.objects.get(codigo="0502")
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

    def test_administrador_configura_pago_en_linea_sin_exponer_secretos(self):
        self.client.force_authenticate(self.admin_empresa)
        response = self.client.patch(
            reverse("empresas-mi-empresa"),
            {
                "pago_en_linea_activo": True,
                "pago_en_linea_proveedor": "paypal",
                "pago_en_linea_modo": "pruebas",
                "pago_en_linea_credencial_publica": "cliente-paypal",
                "pago_en_linea_credencial_secreta": "secreto-paypal",
                "pago_en_linea_webhook_secreto": "webhook-paypal",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.analiza.refresh_from_db()
        self.assertTrue(self.analiza.pago_en_linea_disponible)
        self.assertEqual(self.analiza.pago_en_linea_proveedor, "paypal")
        self.assertEqual(
            response.data["pago_en_linea_credencial_publica"],
            "cliente-paypal",
        )
        self.assertTrue(response.data["pago_en_linea_credencial_secreta_configurada"])
        self.assertTrue(response.data["pago_en_linea_webhook_secreto_configurado"])
        self.assertNotIn("pago_en_linea_credencial_secreta", response.data)
        self.assertNotIn("pago_en_linea_webhook_secreto", response.data)

    def test_pago_en_linea_activo_exige_configuracion_completa(self):
        self.client.force_authenticate(self.admin_empresa)
        response = self.client.patch(
            reverse("empresas-mi-empresa"),
            {
                "pago_en_linea_activo": True,
                "pago_en_linea_proveedor": "paypal",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("pago_en_linea_credencial_publica", response.data)
        self.assertIn("pago_en_linea_credencial_secreta", response.data)
        self.assertIn("pago_en_linea_webhook_secreto", response.data)

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
    def test_admin_gestiona_departamentos_con_paginacion_y_filtros(self):
        self.client.force_authenticate(self.superuser)
        creada = self.client.post(
            reverse("ubicaciones-departamentos"),
            {
                "codigo": "99",
                "nombre": "Departamento prueba",
                "orden": 99,
                "activo": True,
            },
            format="json",
        )

        self.assertEqual(creada.status_code, status.HTTP_201_CREATED)
        self.assertEqual(creada.data["codigo"], "99")
        self.assertEqual(creada.data["nombre"], "Departamento prueba")

        inactivo = Departamento.objects.get(codigo="06")
        inactivo.activo = False
        inactivo.save(update_fields=["activo", "fecha_actualizacion"])
        listado = self.client.get(
            reverse("ubicaciones-departamentos"),
            {
                "incluir_inactivos": "true",
                "buscar": "prueba",
                "orden": "nombre",
            },
        )

        self.assertEqual(listado.status_code, status.HTTP_200_OK)
        self.assertIn("results", listado.data)
        self.assertEqual(listado.data["results"][0]["id"], creada.data["id"])

        inactivas = self.client.get(
            reverse("ubicaciones-departamentos"),
            {"activo": "false", "paginar": "false"},
        )
        self.assertEqual(inactivas.status_code, status.HTTP_200_OK)
        self.assertEqual(len(inactivas.data), 1)
        self.assertEqual(inactivas.data[0]["id"], inactivo.pk)

        actualizada = self.client.patch(
            reverse("ubicaciones-departamentos-detalle", args=[creada.data["id"]]),
            {"nombre": "Departamento prueba norte", "activo": False},
            format="json",
        )
        self.assertEqual(actualizada.status_code, status.HTTP_200_OK)
        self.assertEqual(actualizada.data["nombre"], "Departamento prueba norte")
        self.assertFalse(actualizada.data["activo"])

        eliminada = self.client.delete(
            reverse("ubicaciones-departamentos-detalle", args=[creada.data["id"]])
        )
        self.assertEqual(eliminada.status_code, status.HTTP_204_NO_CONTENT)

    def test_municipios_publicos_devuelven_solo_activos_sin_paginar(self):
        departamento = Departamento.objects.create(
            codigo="99",
            nombre="Departamento prueba",
            orden=99,
        )
        activo = Municipio.objects.create(
            departamento=departamento,
            codigo="9901",
            nombre="Municipio activo",
        )
        Municipio.objects.create(
            departamento=departamento,
            codigo="9902",
            nombre="Municipio inactivo",
            activo=False,
        )

        response = self.client.get(
            reverse("ubicaciones-municipios"),
            {"departamento_id": departamento.pk},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], activo.pk)
        self.assertEqual(response.data[0]["departamento_id"], departamento.pk)

        inactivas_publicas = self.client.get(
            reverse("ubicaciones-municipios"),
            {
                "departamento_id": departamento.pk,
                "activo": "false",
                "incluir_inactivos": "true",
            },
        )
        self.assertEqual(inactivas_publicas.status_code, status.HTTP_200_OK)
        self.assertEqual(len(inactivas_publicas.data), 1)
        self.assertEqual(inactivas_publicas.data[0]["id"], activo.pk)

    def test_ubicaciones_funcionan_en_api_y_api_v1(self):
        for ruta in ("/api/ubicaciones/municipios/", "/api/v1/ubicaciones/municipios/"):
            with self.subTest(ruta=ruta):
                response = self.client.get(
                    ruta,
                    {"departamento_id": self.departamento.pk},
                )
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data[0]["nombre"], "Distrito Central")

    def test_municipios_respetan_permisos_administrativos(self):
        self.client.force_authenticate(self.admin_empresa)
        denegada = self.client.post(
            reverse("ubicaciones-municipios"),
            {
                "codigo": "0899",
                "nombre": "Municipio Prueba Denegado",
                "departamento_id": self.departamento.pk,
            },
            format="json",
        )
        self.assertEqual(denegada.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.superuser)
        response = self.client.post(
            reverse("ubicaciones-municipios"),
            {
                "codigo": "0898",
                "nombre": "Municipio Prueba",
                "departamento_id": self.departamento.pk,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_municipios_rechazan_duplicados_sin_mayusculas_ni_tildes(self):
        Municipio.objects.create(
            departamento=self.departamento,
            codigo="0897",
            nombre="Comayaguela",
        )

        self.client.force_authenticate(self.superuser)
        response = self.client.post(
            reverse("ubicaciones-municipios"),
            {
                "codigo": "0896",
                "nombre": "  Comayagüela  ",
                "departamento_id": self.departamento.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("nombre", response.data)

    def test_sucursales_asignan_municipio_activo(self):
        inactivo = Municipio.objects.create(
            departamento=self.departamento,
            codigo="0895",
            nombre="Municipio Inactivo Test",
            activo=False,
        )

        self.client.force_authenticate(self.admin_empresa)
        creada = self.client.post(
            reverse("empresas-sucursales"),
            {
                "nombre": "Sucursal Centro",
                "municipio_id": self.municipio.pk,
                "direccion": "Centro",
            },
            format="json",
        )

        self.assertEqual(creada.status_code, status.HTTP_201_CREATED)
        self.assertEqual(creada.data["municipio_id"], self.municipio.pk)
        self.assertEqual(creada.data["municipio"], "Distrito Central")
        self.assertEqual(creada.data["departamento_id"], self.departamento.pk)
        self.assertEqual(creada.data["ciudad"], "Distrito Central")
        sucursal = SucursalEmpresa.objects.get(pk=creada.data["id"])
        self.assertEqual(sucursal.municipio_id, self.municipio.pk)
        self.assertEqual(sucursal.ciudad, "Distrito Central")

        response = self.client.post(
            reverse("empresas-sucursales"),
            {
                "nombre": "Sucursal inactiva",
                "municipio_id": inactivo.pk,
                "direccion": "Direccion",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("municipio_id", response.data)

    def test_municipio_vinculado_no_se_elimina_y_puede_desactivarse(self):
        SucursalEmpresa.objects.create(
            empresa=self.analiza,
            municipio=self.municipio,
            nombre="Sucursal Centro",
            direccion="Centro",
        )

        self.client.force_authenticate(self.superuser)
        eliminada = self.client.delete(
            reverse("ubicaciones-municipios-detalle", args=[self.municipio.pk])
        )
        self.assertEqual(eliminada.status_code, status.HTTP_409_CONFLICT)
        self.assertTrue(Municipio.objects.filter(pk=self.municipio.pk).exists())

        desactivada = self.client.patch(
            reverse("ubicaciones-municipios-detalle", args=[self.municipio.pk]),
            {"activo": False},
            format="json",
        )
        self.assertEqual(desactivada.status_code, status.HTTP_200_OK)
        self.assertFalse(desactivada.data["activo"])

    def test_zonas_publicas_muestran_solo_sucursales_activas_agrupadas(self):
        SucursalEmpresa.objects.create(
            empresa=self.analiza,
            municipio=self.municipio,
            nombre="Sucursal Centro",
            direccion="Centro",
        )
        SucursalEmpresa.objects.create(
            empresa=self.analiza,
            municipio=self.choloma,
            nombre="Sucursal Cerrada",
            direccion="Cortes",
            estado=SucursalEmpresa.Estado.TEMPORALMENTE_CERRADA,
        )

        response = self.client.get(
            reverse("empresas-sucursales-zonas"),
            {"empresa_slug": "analiza"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["departamento"], "Francisco Morazan")
        self.assertEqual(response.data[0]["total_sucursales"], 1)
        self.assertEqual(
            response.data[0]["municipios"][0]["municipio"],
            "Distrito Central",
        )

    def test_sucursales_cerca_prioriza_municipio_y_departamento_del_usuario(self):
        valle = Municipio.objects.create(
            departamento=self.departamento,
            codigo="0894",
            nombre="Municipio Vecino Test",
            orden=1022,
        )
        self.comprador.perfil.municipio = self.municipio
        self.comprador.perfil.save(update_fields=["municipio", "fecha_actualizacion"])
        SucursalEmpresa.objects.create(
            empresa=self.analiza,
            municipio=self.municipio,
            nombre="Sucursal local",
            direccion="Centro",
        )
        SucursalEmpresa.objects.create(
            empresa=self.analiza,
            municipio=valle,
            nombre="Sucursal departamental",
            direccion="Valle",
        )

        self.client.force_authenticate(self.comprador)
        response = self.client.get(
            reverse("empresas-sucursales-cerca"),
            {"empresa_slug": "analiza"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["municipio_id"], self.municipio.pk)
        self.assertEqual(
            response.data["sucursales_municipio"][0]["nombre"],
            "Sucursal local",
        )
        self.assertEqual(
            response.data["sucursales_departamento"][0]["nombre"],
            "Sucursal departamental",
        )

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
        principal = SucursalEmpresa.objects.create(
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
        self.assertEqual(response.data[0]["id"], principal.pk)

    def test_admin_gestiona_sucursales_con_paginacion(self):
        self.client.force_authenticate(self.admin_empresa)
        creada = self.client.post(
            reverse("empresas-sucursales"),
            {
                "nombre": "Sucursal Norte",
                "direccion": "Colonia Norte",
                "municipio_id": self.municipio.pk,
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

    def test_delete_sucursal_la_marca_inactiva_sin_eliminarla(self):
        sucursal = SucursalEmpresa.objects.create(
            empresa=self.analiza,
            municipio=self.municipio,
            nombre="Sucursal historica",
            direccion="Centro",
        )

        self.client.force_authenticate(self.admin_empresa)
        response = self.client.delete(
            reverse("empresas-sucursales-detalle", args=[sucursal.pk])
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        sucursal.refresh_from_db()
        self.assertEqual(sucursal.estado, SucursalEmpresa.Estado.INACTIVA)
        self.assertFalse(sucursal.activa)
