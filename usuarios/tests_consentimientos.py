from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.exceptions import PermissionDenied
from django.test import override_settings
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from empresas.models import Departamento, Empresa, Municipio

from .marketing import (
    enviar_correo_promocional,
    perfiles_habilitados_para_promociones,
    validar_comunicacion_promocional,
)
from .models import PerfilUsuario


User = get_user_model()


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="Sistema <no-reply@example.com>",
    TERMINOS_VERSION_ACTUAL="terminos-2.1",
    PRIVACIDAD_VERSION_ACTUAL="privacidad-3.0",
)
class ConsentimientosAPITests(APITestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Empresa consentimiento",
            slug="empresa-consentimiento",
            subdominio="empresa-consentimiento",
            correo="privacidad@empresa.test",
            telefono="22334455",
            direccion="Tegucigalpa",
            sitio_web="https://empresa.test",
        )
        self.otra_empresa = Empresa.objects.create(
            nombre="Otra empresa consentimiento",
            slug="otra-empresa-consentimiento",
            subdominio="otra-empresa-consentimiento",
        )
        self.departamento = Departamento.objects.get(codigo="08")
        self.municipio = Municipio.objects.get(codigo="0801")

    def datos_registro(self, **cambios):
        datos = {
            "empresa_slug": self.empresa.slug,
            "nombre": "Maria",
            "apellido": "Rivera",
            "email": "maria-consentimiento@example.com",
            "telefono": "99999999",
            "numero_identidad": "0801199912399",
            "departamento_id": self.departamento.pk,
            "municipio_id": self.municipio.pk,
            "password": "ClaveSegura123!",
            "password_confirmacion": "ClaveSegura123!",
            "acepta_terminos": True,
            "acepta_privacidad": True,
        }
        datos.update(cambios)
        return datos

    def crear_comprador(self, empresa=None, email="cliente@example.com"):
        usuario = User.objects.create_user(
            username=email,
            email=email,
            password="ClaveSegura123!",
            is_active=True,
        )
        perfil = usuario.perfil
        perfil.empresa = empresa or self.empresa
        perfil.municipio = self.municipio
        perfil.telefono = "99887766"
        perfil.correo_verificado = True
        perfil.activo = True
        perfil.save()
        return usuario

    def test_registro_guarda_aceptacion_legal_y_promociones_opcionales(self):
        respuesta = self.client.post(
            reverse("usuarios-registro-comprador"),
            self.datos_registro(acepta_promociones=True),
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        perfil = User.objects.get(
            email="maria-consentimiento@example.com"
        ).perfil
        self.assertTrue(perfil.acepta_terminos)
        self.assertTrue(perfil.acepta_privacidad)
        self.assertIsNotNone(perfil.fecha_aceptacion_terminos_privacidad)
        self.assertEqual(perfil.version_terminos_aceptada, "terminos-2.1")
        self.assertEqual(perfil.version_privacidad_aceptada, "privacidad-3.0")
        self.assertTrue(perfil.acepta_promociones)
        self.assertIsNotNone(perfil.fecha_aceptacion_promociones)
        self.assertIsNone(perfil.fecha_retiro_promociones)
        self.assertEqual(len(mail.outbox), 1)

    def test_registro_sin_promociones_las_deja_desactivadas_y_envia_codigo(self):
        respuesta = self.client.post(
            reverse("usuarios-registro-comprador"),
            self.datos_registro(),
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        perfil = User.objects.get(
            email="maria-consentimiento@example.com"
        ).perfil
        self.assertFalse(perfil.acepta_promociones)
        self.assertIsNone(perfil.fecha_aceptacion_promociones)
        self.assertIsNone(perfil.fecha_retiro_promociones)
        self.assertEqual(len(mail.outbox), 1)

    def test_registro_acepta_casilla_legal_combinada(self):
        datos = self.datos_registro()
        datos.pop("acepta_terminos")
        datos.pop("acepta_privacidad")
        datos["acepta_terminos_privacidad"] = True

        respuesta = self.client.post(
            reverse("usuarios-registro-comprador"),
            datos,
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        perfil = User.objects.get(
            email="maria-consentimiento@example.com"
        ).perfil
        self.assertTrue(perfil.acepta_terminos)
        self.assertTrue(perfil.acepta_privacidad)

    def test_registro_rechaza_omitir_aceptacion_legal(self):
        datos = self.datos_registro()
        datos.pop("acepta_terminos")
        datos.pop("acepta_privacidad")

        respuesta = self.client.post(
            reverse("usuarios-registro-comprador"),
            datos,
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("acepta_terminos", respuesta.data)

    def test_aviso_legal_identifica_empresa_y_cubre_secciones_requeridas(self):
        for url in (
            "/api/usuarios/aviso-legal/",
            "/api/v1/usuarios/aviso-legal/",
        ):
            with self.subTest(url=url):
                respuesta = self.client.get(
                    url,
                    {"empresa_slug": self.empresa.slug},
                )
                self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
                self.assertEqual(respuesta.data["empresa"]["nombre"], self.empresa.nombre)
                self.assertEqual(
                    respuesta.data["documentos"]["terminos"]["version"],
                    "terminos-2.1",
                )
                claves = {
                    seccion["clave"] for seccion in respuesta.data["secciones"]
                }
                self.assertTrue(
                    {
                        "tratamiento",
                        "conservacion",
                        "proveedores",
                        "derechos",
                        "compras",
                        "uso_sanitario",
                        "promociones",
                    }.issubset(claves)
                )

    def test_preferencia_solo_modifica_usuario_autenticado_y_audita_retiro(self):
        usuario = self.crear_comprador()
        otro = self.crear_comprador(
            email="otro-consentimiento@example.com"
        )
        otro.perfil.actualizar_preferencia_promociones(True)
        self.client.force_authenticate(usuario)
        url = reverse("usuarios-preferencias-comunicacion")

        inicial = self.client.get(url)
        aceptacion = self.client.patch(
            url,
            {"acepta_promociones": True},
            format="json",
        )
        retiro = self.client.patch(
            url,
            {"acepta_promociones": False},
            format="json",
        )
        fecha_retiro = retiro.data["fecha_retiro_promociones"]
        repetido = self.client.patch(
            url,
            {"acepta_promociones": False},
            format="json",
        )

        self.assertEqual(inicial.status_code, status.HTTP_200_OK)
        self.assertFalse(inicial.data["acepta_promociones"])
        self.assertTrue(aceptacion.data["acepta_promociones"])
        self.assertIsNotNone(aceptacion.data["fecha_aceptacion_promociones"])
        self.assertFalse(retiro.data["acepta_promociones"])
        self.assertEqual(repetido.data["fecha_retiro_promociones"], fecha_retiro)
        otro.perfil.refresh_from_db()
        self.assertTrue(otro.perfil.acepta_promociones)

    def test_preferencia_requiere_autenticacion_y_valor_booleano(self):
        url = reverse("usuarios-preferencias-comunicacion")
        sin_sesion = self.client.get(url)
        usuario = self.crear_comprador()
        self.client.force_authenticate(usuario)
        sin_campo = self.client.patch(url, {}, format="json")

        self.assertEqual(sin_sesion.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(sin_campo.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("acepta_promociones", sin_campo.data)

    @patch("usuarios.marketing.send_mail", return_value=1)
    def test_publicidad_se_bloquea_sin_consentimiento(self, enviar_mock):
        usuario = self.crear_comprador()

        with self.assertRaises(PermissionDenied):
            enviar_correo_promocional(
                usuario=usuario,
                asunto="Promocion",
                mensaje="Mensaje comercial",
            )

        enviar_mock.assert_not_called()
        self.assertFalse(
            perfiles_habilitados_para_promociones(
                self.empresa,
                "correo",
            ).filter(usuario=usuario).exists()
        )

    @patch("usuarios.marketing.send_mail", return_value=1)
    def test_publicidad_permitida_solo_para_empresa_y_canal_autorizados(
        self,
        enviar_mock,
    ):
        usuario = self.crear_comprador()
        ajeno = self.crear_comprador(
            empresa=self.otra_empresa,
            email="ajeno-consentimiento@example.com",
        )
        usuario.perfil.actualizar_preferencia_promociones(True)
        ajeno.perfil.actualizar_preferencia_promociones(True)

        validar_comunicacion_promocional(usuario, "telefono")
        enviados = enviar_correo_promocional(
            usuario=usuario,
            asunto="Promocion autorizada",
            mensaje="Mensaje comercial",
        )
        destinatarios = perfiles_habilitados_para_promociones(
            self.empresa,
            "correo",
        )

        self.assertEqual(enviados, 1)
        enviar_mock.assert_called_once()
        self.assertTrue(destinatarios.filter(usuario=usuario).exists())
        self.assertFalse(destinatarios.filter(usuario=ajeno).exists())
