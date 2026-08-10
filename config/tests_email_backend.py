import base64
import io
import json
from urllib.error import HTTPError, URLError
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMessage, EmailMultiAlternatives, send_mail
from django.test import SimpleTestCase, override_settings

from .email_backends import BrevoAPIEmailBackend, BrevoAPIError


class RespuestaBrevoFalsa:
    status = 201

    def __init__(self, contenido=b'{"messageId":"mensaje-123"}'):
        self.contenido = contenido

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return self.contenido


class BrevoAPIEmailBackendTests(SimpleTestCase):
    def crear_backend(self, **opciones):
        valores = {
            "api_key": "clave-api-prueba",
            "api_url": "https://api.brevo.test/v3/smtp/email",
            "timeout": 8,
        }
        valores.update(opciones)
        return BrevoAPIEmailBackend(**valores)

    @patch("config.email_backends.urlopen")
    def test_envia_texto_por_https_y_conserva_message_id(self, urlopen_mock):
        urlopen_mock.return_value = RespuestaBrevoFalsa()
        mensaje = EmailMessage(
            subject="Codigo de verificacion",
            body="Tu codigo es 123456",
            from_email="Analiza <remitente@example.com>",
            to=["Cliente <cliente@example.com>"],
        )

        enviados = self.crear_backend().send_messages([mensaje])

        self.assertEqual(enviados, 1)
        self.assertEqual(mensaje.brevo_message_id, "mensaje-123")
        solicitud = urlopen_mock.call_args.args[0]
        payload = json.loads(solicitud.data.decode("utf-8"))
        self.assertEqual(solicitud.full_url, "https://api.brevo.test/v3/smtp/email")
        self.assertEqual(solicitud.method, "POST")
        self.assertEqual(solicitud.get_header("Api-key"), "clave-api-prueba")
        self.assertEqual(payload["sender"]["email"], "remitente@example.com")
        self.assertEqual(payload["to"][0]["email"], "cliente@example.com")
        self.assertEqual(payload["textContent"], "Tu codigo es 123456")
        self.assertEqual(urlopen_mock.call_args.kwargs["timeout"], 8)

    @patch("config.email_backends.urlopen")
    def test_envia_html_y_pdf_adjunto(self, urlopen_mock):
        urlopen_mock.return_value = RespuestaBrevoFalsa()
        mensaje = EmailMultiAlternatives(
            subject="Prefactura",
            body="Prefactura adjunta",
            from_email="remitente@example.com",
            to=["cliente@example.com"],
        )
        mensaje.attach_alternative("<p>Prefactura adjunta</p>", "text/html")
        mensaje.attach("prefactura.pdf", b"%PDF-prueba", "application/pdf")

        enviados = self.crear_backend().send_messages([mensaje])

        self.assertEqual(enviados, 1)
        solicitud = urlopen_mock.call_args.args[0]
        payload = json.loads(solicitud.data.decode("utf-8"))
        self.assertEqual(payload["htmlContent"], "<p>Prefactura adjunta</p>")
        self.assertEqual(payload["attachment"][0]["name"], "prefactura.pdf")
        self.assertEqual(
            base64.b64decode(payload["attachment"][0]["content"]),
            b"%PDF-prueba",
        )

    @patch("config.email_backends.urlopen")
    def test_expone_error_http_sin_filtrar_la_clave(self, urlopen_mock):
        urlopen_mock.side_effect = HTTPError(
            url="https://api.brevo.test/v3/smtp/email",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=io.BytesIO(b'{"message":"Key not found"}'),
        )
        backend = self.crear_backend()

        with self.assertRaisesMessage(BrevoAPIError, "HTTP 401: Key not found"):
            backend.send_messages(
                [EmailMessage("Asunto", "Mensaje", to=["cliente@example.com"])]
            )

    @patch("config.email_backends.urlopen", side_effect=URLError("sin conexion"))
    def test_fail_silently_devuelve_cero(self, _urlopen_mock):
        backend = self.crear_backend(fail_silently=True)

        with self.assertLogs("config.email_backends", level="ERROR"):
            enviados = backend.send_messages(
                [EmailMessage("Asunto", "Mensaje", to=["cliente@example.com"])]
            )

        self.assertEqual(enviados, 0)

    def test_exige_api_key(self):
        backend = self.crear_backend(api_key="")

        with self.assertRaises(ImproperlyConfigured):
            backend.send_messages(
                [EmailMessage("Asunto", "Mensaje", to=["cliente@example.com"])]
            )

    @override_settings(
        EMAIL_BACKEND="config.email_backends.BrevoAPIEmailBackend",
        BREVO_API_KEY="clave-api-prueba",
        BREVO_API_URL="https://api.brevo.test/v3/smtp/email",
        BREVO_API_TIMEOUT=8,
        DEFAULT_FROM_EMAIL="Analiza <remitente@example.com>",
    )
    @patch("config.email_backends.urlopen")
    def test_django_send_mail_usa_el_backend_brevo(self, urlopen_mock):
        urlopen_mock.return_value = RespuestaBrevoFalsa()

        enviados = send_mail(
            "Codigo de verificacion",
            "Tu codigo es 123456",
            None,
            ["cliente@example.com"],
        )

        self.assertEqual(enviados, 1)
        payload = json.loads(urlopen_mock.call_args.args[0].data.decode("utf-8"))
        self.assertEqual(payload["sender"]["email"], "remitente@example.com")
