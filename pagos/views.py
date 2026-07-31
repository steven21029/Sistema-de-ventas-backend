import hashlib
import hmac

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404

from rest_framework import decorators, response, status, viewsets
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from pedidos.models import Pedido

from .models import EventoWebhookPago, Pago
from .permissions import IsPagoOwnerOrEmpresaStaff
from .serializers import IniciarPagoSerializer, PagoSerializer, WebhookPagoSerializer


class PagoViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PagoSerializer
    permission_classes = [IsPagoOwnerOrEmpresaStaff]
    lookup_field = "referencia"

    def get_queryset(self):
        queryset = Pago.objects.select_related("pedido", "empresa", "usuario")
        user = self.request.user
        if user.is_superuser:
            return queryset

        perfil = getattr(user, "perfil", None)
        if not perfil or not perfil.activo:
            return queryset.none()
        if perfil.es_administrador_maestro:
            return queryset
        if not perfil.empresa_id:
            return queryset.none()
        if perfil.es_administrador_empresa or perfil.es_gerente:
            return queryset.filter(empresa=perfil.empresa)
        return queryset.filter(empresa=perfil.empresa, usuario=user)

    @decorators.action(detail=False, methods=["post"], url_path="iniciar")
    def iniciar(self, request):
        entrada = IniciarPagoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        pedido = self._obtener_pedido_pagable(entrada.validated_data["pedido_id"])
        proveedor = settings.PAGOS_PROVEEDOR_DEFAULT.strip()
        if not proveedor:
            raise APIException("No hay un proveedor de pagos configurado.")

        try:
            pago, creado = Pago.obtener_o_crear_pendiente(pedido, proveedor)
        except DjangoValidationError as exc:
            raise ValidationError(self._normalizar_error(exc)) from exc

        salida = PagoSerializer(pago)
        return response.Response(
            salida.data,
            status=status.HTTP_201_CREATED if creado else status.HTTP_200_OK,
        )

    def _obtener_pedido_pagable(self, pedido_id):
        user = self.request.user
        queryset = Pedido.objects.select_related("empresa", "usuario")
        if user.is_superuser:
            return get_object_or_404(queryset, pk=pedido_id)

        perfil = getattr(user, "perfil", None)
        if not perfil or not perfil.activo or not perfil.empresa_id:
            raise PermissionDenied("Tu perfil no tiene una empresa activa.")
        return get_object_or_404(
            queryset,
            pk=pedido_id,
            empresa=perfil.empresa,
            usuario=user,
        )

    def _normalizar_error(self, error):
        if hasattr(error, "message_dict"):
            return error.message_dict
        return {"detail": error.messages}


class WebhookPagoView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, proveedor):
        payload_crudo = request.body
        self._validar_firma(payload_crudo, request.headers.get("X-Pago-Signature", ""))

        entrada = WebhookPagoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data
        hash_payload = hashlib.sha256(payload_crudo).hexdigest()

        try:
            evento, creado = EventoWebhookPago.objects.get_or_create(
                proveedor=proveedor,
                evento_id=datos["evento_id"],
                defaults={
                    "referencia_pago": datos["referencia"],
                    "estado_recibido": datos["estado"],
                    "hash_payload": hash_payload,
                },
            )
        except IntegrityError:
            evento = EventoWebhookPago.objects.get(
                proveedor=proveedor,
                evento_id=datos["evento_id"],
            )
            creado = False

        if not creado:
            if evento.hash_payload != hash_payload:
                raise ValidationError(
                    {"evento_id": "El evento ya existe con un contenido diferente."}
                )
            if evento.procesado:
                return response.Response(
                    {"procesado": True, "duplicado": True},
                    status=status.HTTP_200_OK,
                )

        try:
            with transaction.atomic():
                pago, _cambio = Pago.procesar_resultado(
                    referencia=datos["referencia"],
                    proveedor=proveedor,
                    estado=datos["estado"],
                    identificador_externo=datos["identificador_externo"],
                    codigo_respuesta=datos["codigo_respuesta"],
                )
                evento.pago = pago
                evento.procesado = True
                evento.mensaje = "Evento procesado correctamente."
                evento.save(
                    update_fields=[
                        "pago",
                        "procesado",
                        "mensaje",
                        "fecha_actualizacion",
                    ]
                )
        except (DjangoValidationError, Pago.DoesNotExist) as exc:
            evento.mensaje = str(exc)[:250]
            evento.save(update_fields=["mensaje", "fecha_actualizacion"])
            if isinstance(exc, Pago.DoesNotExist):
                raise ValidationError(
                    {"referencia": "No existe un pago con esta referencia."}
                ) from exc
            if hasattr(exc, "message_dict"):
                raise ValidationError(exc.message_dict) from exc
            raise ValidationError({"detail": exc.messages}) from exc

        return response.Response(
            {"procesado": True, "duplicado": False},
            status=status.HTTP_200_OK,
        )

    def _validar_firma(self, payload, firma_recibida):
        secreto = settings.PAGOS_WEBHOOK_SECRET
        if not secreto:
            error = APIException("El secreto de webhooks de pagos no esta configurado.")
            error.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            raise error

        firma = firma_recibida.removeprefix("sha256=").strip().lower()
        esperada = hmac.new(
            secreto.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        if not firma or not hmac.compare_digest(firma, esperada):
            raise PermissionDenied("La firma del webhook no es valida.")
