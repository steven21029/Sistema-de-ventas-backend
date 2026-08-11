from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

from empresas.models import Empresa

from .models import CodigoVerificacionCorreo, PerfilUsuario


User = get_user_model()


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="Analiza <no-reply@example.com>",
)
class RegistroCompradorAPITests(APITestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Analiza",
            slug="analiza-registro",
            subdominio="analiza-registro",
        )
        self.url_registro = "/api/v1/usuarios/registro-comprador/"
        self.url_reenvio = "/api/v1/usuarios/reenviar-verificacion/"

    def datos_validos(self, **cambios):
        datos = {
            "empresa_slug": self.empresa.slug,
            "nombre_completo": "Jose Maria Rivera",
            "email": "nuevo-comprador@example.com",
            "telefono": "99999999",
            "numero_identidad": "0801199912345",
            "password": "ClaveSegura123!",
            "password_confirmacion": "ClaveSegura123!",
            "acepta_terminos": True,
            "acepta_privacidad": True,
        }
        datos.update(cambios)
        return datos

    def test_rechaza_nombre_con_numeros(self):
        respuesta = self.client.post(
            self.url_registro,
            self.datos_validos(nombre_completo="Oscar161"),
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("nombre_completo", respuesta.data)
        self.assertIn("letras", str(respuesta.data["nombre_completo"][0]))

    def test_rechaza_telefono_con_caracteres_no_numericos(self):
        respuesta = self.client.post(
            self.url_registro,
            self.datos_validos(telefono="9999-9999"),
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("telefono", respuesta.data)
        self.assertIn("numeros", str(respuesta.data["telefono"][0]))

    def test_rechaza_identidad_con_letras(self):
        respuesta = self.client.post(
            self.url_registro,
            self.datos_validos(numero_identidad="080119991234A"),
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("numero_identidad", respuesta.data)

    def test_registro_normaliza_nombre_y_envia_codigo(self):
        respuesta = self.client.post(
            self.url_registro,
            self.datos_validos(nombre_completo="Jose   Maria Rivera"),
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        usuario = User.objects.get(email="nuevo-comprador@example.com")
        perfil = usuario.perfil
        codigo = CodigoVerificacionCorreo.objects.get(usuario=usuario, usado=False)
        self.assertEqual(usuario.first_name, "Jose")
        self.assertEqual(usuario.last_name, "Maria Rivera")
        self.assertFalse(usuario.is_active)
        self.assertFalse(perfil.correo_verificado)
        self.assertEqual(perfil.telefono, "99999999")
        self.assertTrue(codigo.puede_usarse)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [usuario.email])
        self.assertIn(codigo.codigo, mail.outbox[0].body)

    def test_reenvio_crea_codigo_nuevo_y_envia_otro_correo(self):
        self.client.post(
            self.url_registro,
            self.datos_validos(),
            format="json",
        )
        usuario = User.objects.get(email="nuevo-comprador@example.com")
        anterior = CodigoVerificacionCorreo.objects.get(usuario=usuario)
        CodigoVerificacionCorreo.objects.filter(pk=anterior.pk).update(
            fecha_creacion=timezone.now()
            - timedelta(
                seconds=CodigoVerificacionCorreo.ESPERA_REENVIO_SEGUNDOS + 1
            )
        )

        respuesta = self.client.post(
            self.url_reenvio,
            {"email": usuario.email},
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        anterior.refresh_from_db()
        nuevo = CodigoVerificacionCorreo.objects.filter(usuario=usuario).first()
        self.assertTrue(anterior.usado)
        self.assertNotEqual(nuevo.pk, anterior.pk)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[-1].to, [usuario.email])

    @patch("usuarios.models.send_mail", return_value=0)
    def test_registro_devuelve_503_y_revierte_si_brevo_no_confirma(self, _send_mail):
        respuesta = self.client.post(
            self.url_registro,
            self.datos_validos(),
            format="json",
        )

        self.assertEqual(
            respuesta.status_code,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )
        self.assertFalse(
            User.objects.filter(email="nuevo-comprador@example.com").exists()
        )
        self.assertFalse(CodigoVerificacionCorreo.objects.exists())


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="Analiza <no-reply@example.com>",
)
class RecuperacionContrasenaAPITests(APITestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Analiza recuperacion",
            slug="analiza-recuperacion",
            subdominio="analiza-recuperacion",
        )
        self.usuario = User.objects.create_user(
            username="recupera@example.com",
            email="recupera@example.com",
            password="ClaveSegura123!",
            is_active=True,
        )
        perfil = self.usuario.perfil
        perfil.empresa = self.empresa
        perfil.correo_verificado = True
        perfil.activo = True
        perfil.save()
        self.url_solicitar = "/api/v1/usuarios/solicitar-recuperacion-contrasena/"
        self.url_confirmar = "/api/v1/usuarios/confirmar-recuperacion-contrasena/"

    def test_solicita_codigo_y_confirma_contrasena_revocando_sesiones(self):
        refresh = RefreshToken.for_user(self.usuario)

        respuesta = self.client.post(
            self.url_solicitar,
            {"email": self.usuario.email},
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        codigo = CodigoVerificacionCorreo.objects.get(
            usuario=self.usuario,
            tipo=CodigoVerificacionCorreo.Tipo.RECUPERACION_CONTRASENA,
            usado=False,
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(codigo.codigo, mail.outbox[0].body)

        confirmacion = self.client.post(
            self.url_confirmar,
            {
                "email": self.usuario.email,
                "codigo": codigo.codigo,
                "password": "NuevaClave123!",
                "password_confirmacion": "NuevaClave123!",
            },
            format="json",
        )

        self.assertEqual(confirmacion.status_code, status.HTTP_200_OK)
        self.usuario.refresh_from_db()
        codigo.refresh_from_db()
        self.assertTrue(self.usuario.check_password("NuevaClave123!"))
        self.assertTrue(codigo.usado)
        self.assertTrue(
            BlacklistedToken.objects.filter(token__jti=refresh["jti"]).exists()
        )


class ValidacionesAdministrativasTests(APITestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Empresa usuarios",
            slug="empresa-usuarios-validacion",
            subdominio="empresa-usuarios-validacion",
        )
        self.superuser = User.objects.create_superuser(
            username="root-validaciones",
            email="root-validaciones@example.com",
            password="ClaveSegura123!",
        )
        self.client.force_authenticate(self.superuser)
        self.url = "/api/v1/usuarios/administracion/"

    def datos_validos(self, **cambios):
        datos = {
            "username": "usuario-validado",
            "email": "usuario-validado@example.com",
            "first_name": "Maria",
            "last_name": "Rivera",
            "password": "ClaveSegura123!",
            "empresa": self.empresa.pk,
            "rol": PerfilUsuario.Rol.COMPRADOR,
            "telefono": "88888888",
            "numero_identidad": "0801199912346",
            "correo_verificado": True,
        }
        datos.update(cambios)
        return datos

    def test_administracion_rechaza_nombre_telefono_e_identidad_invalidos(self):
        casos = (
            ("first_name", "Maria123"),
            ("telefono", "telefono"),
            ("numero_identidad", "080119991234A"),
        )
        for campo, valor in casos:
            with self.subTest(campo=campo):
                respuesta = self.client.post(
                    self.url,
                    self.datos_validos(**{campo: valor}),
                    format="json",
                )
                self.assertEqual(
                    respuesta.status_code,
                    status.HTTP_400_BAD_REQUEST,
                )
                self.assertIn(campo, respuesta.data)
