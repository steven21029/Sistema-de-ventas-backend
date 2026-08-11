from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken


class AutenticacionJWTTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.password = "ClaveSegura123!"
        self.usuario = get_user_model().objects.create_user(
            username="cliente@example.com",
            email="cliente@example.com",
            password=self.password,
            is_active=True,
        )
        self.usuario.perfil.correo_verificado = True
        self.usuario.perfil.save(update_fields=["correo_verificado"])

    def iniciar_sesion(self, **extras):
        datos = {
            "email": self.usuario.email,
            "password": self.password,
        }
        datos.update(extras)
        return self.client.post(
            "/api/usuarios/login/",
            datos,
            format="json",
        )

    def test_login_oculta_refresh_y_limita_duracion(self):
        respuesta = self.iniciar_sesion()

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("access", respuesta.data)
        self.assertNotIn("refresh", respuesta.data)

        cookie = respuesta.cookies[settings.JWT_REFRESH_COOKIE_NAME]
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["path"], "/api/")
        self.assertEqual(
            cookie["samesite"],
            settings.JWT_REFRESH_COOKIE_SAMESITE,
        )
        self.assertEqual(
            int(cookie["max-age"]),
            settings.JWT_SESSION_MAX_SECONDS,
        )

        access = AccessToken(respuesta.data["access"])
        refresh = RefreshToken(cookie.value)
        self.assertEqual(int(access["exp"]) - int(access["iat"]), 15 * 60)
        self.assertEqual(int(refresh["exp"]) - int(refresh["iat"]), 5 * 60 * 60)

    def test_login_recordarme_extiende_cookie_y_refresh(self):
        duracion_recordarme = 30 * 24 * 60 * 60

        with self.settings(JWT_REMEMBER_ME_SECONDS=duracion_recordarme):
            respuesta = self.iniciar_sesion(recordarme=True)

        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn("refresh", respuesta.data)
        cookie = respuesta.cookies[settings.JWT_REFRESH_COOKIE_NAME]
        self.assertEqual(int(cookie["max-age"]), duracion_recordarme)

        refresh = RefreshToken(cookie.value)
        self.assertEqual(
            int(refresh["exp"]) - int(refresh["iat"]),
            duracion_recordarme,
        )
        token_pendiente = OutstandingToken.objects.get(jti=refresh["jti"])
        self.assertEqual(
            int(token_pendiente.expires_at.timestamp()),
            int(refresh["exp"]),
        )

    def test_refresh_se_lee_desde_cookie(self):
        login = self.iniciar_sesion()
        self.client.cookies[settings.JWT_REFRESH_COOKIE_NAME] = (
            login.cookies[settings.JWT_REFRESH_COOKIE_NAME].value
        )

        respuesta = self.client.post(
            "/api/usuarios/token/refresh/",
            {},
            format="json",
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("access", respuesta.data)
        self.assertNotIn("refresh", respuesta.data)

    def test_refresh_acepta_ruta_versionada(self):
        login = self.iniciar_sesion()
        self.client.cookies[settings.JWT_REFRESH_COOKIE_NAME] = (
            login.cookies[settings.JWT_REFRESH_COOKIE_NAME].value
        )

        respuesta = self.client.post(
            "/api/v1/usuarios/token/refresh/",
            {},
            format="json",
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("access", respuesta.data)

    def test_access_renovado_no_supera_fin_de_sesion(self):
        refresh = RefreshToken.for_user(self.usuario)
        refresh.set_exp(
            from_time=timezone.now(),
            lifetime=timedelta(minutes=5),
        )
        self.client.cookies[settings.JWT_REFRESH_COOKIE_NAME] = str(refresh)

        respuesta = self.client.post(
            "/api/usuarios/token/refresh/",
            {},
            format="json",
        )

        self.assertEqual(respuesta.status_code, 200)
        access = AccessToken(respuesta.data["access"])
        self.assertEqual(int(access["exp"]), int(refresh["exp"]))

    def test_logout_bloquea_refresh_y_elimina_cookie(self):
        login = self.iniciar_sesion()
        refresh = login.cookies[settings.JWT_REFRESH_COOKIE_NAME].value
        self.client.cookies[settings.JWT_REFRESH_COOKIE_NAME] = refresh

        logout = self.client.post(
            "/api/usuarios/token/logout/",
            {},
            format="json",
        )

        self.assertEqual(logout.status_code, 200)
        self.assertEqual(
            logout.cookies[settings.JWT_REFRESH_COOKIE_NAME]["max-age"],
            0,
        )

        self.client.cookies[settings.JWT_REFRESH_COOKIE_NAME] = refresh
        renovacion = self.client.post(
            "/api/usuarios/token/refresh/",
            {},
            format="json",
        )
        self.assertEqual(renovacion.status_code, 401)
