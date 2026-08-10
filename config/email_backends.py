import base64
import json
import logging
from email.mime.base import MIMEBase
from email.utils import parseaddr
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import BadHeaderError
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.message import sanitize_address


logger = logging.getLogger(__name__)


class BrevoAPIError(Exception):
    pass


class BrevoAPIEmailBackend(BaseEmailBackend):
    def __init__(
        self,
        fail_silently=False,
        api_key=None,
        api_url=None,
        timeout=None,
        **kwargs,
    ):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.api_key = api_key if api_key is not None else settings.BREVO_API_KEY
        self.api_url = api_url or settings.BREVO_API_URL
        self.timeout = timeout if timeout is not None else settings.BREVO_API_TIMEOUT

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        enviados = 0
        for mensaje in email_messages:
            try:
                message_id = self._send_message(mensaje)
            except Exception:
                if not self.fail_silently:
                    raise
                logger.exception("Brevo API rechazo un correo transaccional.")
                continue

            if message_id:
                mensaje.brevo_message_id = message_id
                enviados += 1
                logger.info(
                    "Brevo API acepto un correo. message_id=%s",
                    message_id,
                )

        return enviados

    def _send_message(self, mensaje):
        if not self.api_key:
            raise ImproperlyConfigured(
                "BREVO_API_KEY es obligatoria para enviar correos."
            )
        if "\r" in mensaje.subject or "\n" in mensaje.subject:
            raise BadHeaderError("El asunto del correo contiene saltos de linea.")

        payload = self._crear_payload(mensaje)
        if not payload.get("to") and not payload.get("cc") and not payload.get("bcc"):
            return None

        solicitud = Request(
            self.api_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "accept": "application/json",
                "api-key": self.api_key,
                "content-type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(solicitud, timeout=self.timeout) as respuesta:
                estado = respuesta.status
                contenido = respuesta.read()
        except HTTPError as exc:
            detalle = self._detalle_error(exc.read())
            raise BrevoAPIError(
                f"Brevo API respondio HTTP {exc.code}: {detalle}"
            ) from exc
        except URLError as exc:
            raise BrevoAPIError(
                "No fue posible conectar con Brevo API."
            ) from exc

        if estado < 200 or estado >= 300:
            raise BrevoAPIError(f"Brevo API respondio HTTP {estado}.")

        try:
            datos = json.loads(contenido.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BrevoAPIError("Brevo API devolvio una respuesta invalida.") from exc

        message_id = datos.get("messageId", "").strip()
        if not message_id:
            raise BrevoAPIError("Brevo API no devolvio el identificador del correo.")
        return message_id

    def _crear_payload(self, mensaje):
        from_email = mensaje.from_email or settings.DEFAULT_FROM_EMAIL
        payload = {
            "sender": self._direccion(from_email),
            "to": [self._direccion(direccion) for direccion in mensaje.to],
            "subject": mensaje.subject,
        }
        if mensaje.cc:
            payload["cc"] = [self._direccion(direccion) for direccion in mensaje.cc]
        if mensaje.bcc:
            payload["bcc"] = [self._direccion(direccion) for direccion in mensaje.bcc]
        if mensaje.reply_to:
            payload["replyTo"] = self._direccion(mensaje.reply_to[0])

        html = self._contenido_html(mensaje)
        if mensaje.body and mensaje.content_subtype == "html":
            payload["htmlContent"] = mensaje.body
        else:
            payload["textContent"] = mensaje.body or ""
            if html:
                payload["htmlContent"] = html

        adjuntos = self._adjuntos(mensaje)
        if adjuntos:
            payload["attachment"] = adjuntos
        return payload

    def _direccion(self, direccion):
        limpia = sanitize_address(direccion, "utf-8")
        nombre, correo = parseaddr(limpia)
        if not correo:
            raise BrevoAPIError("El correo contiene una direccion invalida.")
        resultado = {"email": correo}
        if nombre:
            resultado["name"] = nombre
        return resultado

    def _contenido_html(self, mensaje):
        for alternativa in getattr(mensaje, "alternatives", []):
            contenido = getattr(alternativa, "content", alternativa[0])
            mimetype = getattr(alternativa, "mimetype", alternativa[1])
            if mimetype == "text/html":
                return contenido
        return ""

    def _adjuntos(self, mensaje):
        resultado = []
        for adjunto in mensaje.attachments:
            if isinstance(adjunto, MIMEBase):
                nombre = adjunto.get_filename() or "adjunto"
                contenido = adjunto.get_payload(decode=True) or b""
            else:
                nombre = getattr(adjunto, "filename", adjunto[0]) or "adjunto"
                contenido = getattr(adjunto, "content", adjunto[1])
                if isinstance(contenido, str):
                    contenido = contenido.encode("utf-8")
            resultado.append(
                {
                    "name": nombre,
                    "content": base64.b64encode(contenido).decode("ascii"),
                }
            )
        return resultado

    def _detalle_error(self, contenido):
        try:
            datos = json.loads(contenido.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return "respuesta sin detalle"
        return str(datos.get("message") or datos.get("code") or "error desconocido")
