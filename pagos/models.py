import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils import timezone

from empresas.models import Empresa
from pedidos.models import Pedido


class Pago(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        APROBADO = "aprobado", "Aprobado"
        RECHAZADO = "rechazado", "Rechazado"
        CANCELADO = "cancelado", "Cancelado"

    class Metodo(models.TextChoices):
        EN_LINEA = "en_linea", "Pago en linea"
        SUCURSAL = "sucursal", "Pago en sucursal"

    CAMPOS_INMUTABLES = (
        "pedido_id",
        "empresa_id",
        "usuario_id",
        "referencia",
        "proveedor",
        "metodo",
        "monto",
        "moneda",
    )
    CAMPOS_RESULTADO = (
        "identificador_externo",
        "codigo_respuesta",
        "fecha_confirmacion",
    )

    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.PROTECT,
        related_name="pagos",
    )
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name="pagos",
        editable=False,
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="pagos",
        editable=False,
    )
    referencia = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    proveedor = models.CharField(max_length=50)
    metodo = models.CharField(
        max_length=20,
        choices=Metodo.choices,
        default=Metodo.EN_LINEA,
    )
    identificador_externo = models.CharField(max_length=150, blank=True)
    monto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        editable=False,
    )
    moneda = models.CharField(max_length=3, editable=False)
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
    )
    url_pago = models.URLField(blank=True)
    codigo_respuesta = models.CharField(max_length=100, blank=True)
    fecha_confirmacion = models.DateTimeField(null=True, blank=True, editable=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion", "-id"]
        verbose_name = "pago"
        verbose_name_plural = "pagos"
        constraints = [
            models.UniqueConstraint(
                fields=["pedido"],
                condition=models.Q(estado="pendiente"),
                name="pago_pendiente_unico_por_pedido",
            ),
            models.UniqueConstraint(
                fields=["proveedor", "identificador_externo"],
                condition=~models.Q(identificador_externo=""),
                name="pago_identificador_externo_unico",
            ),
            models.CheckConstraint(
                condition=models.Q(monto__gt=0),
                name="pago_monto_mayor_cero",
            ),
        ]
        indexes = [
            models.Index(fields=["empresa", "estado"]),
            models.Index(fields=["empresa", "metodo", "estado"]),
            models.Index(fields=["proveedor", "estado"]),
        ]

    def __str__(self):
        return f"Pago {self.referencia} - {self.get_estado_display()}"

    def clean(self):
        super().clean()
        if not self.pedido_id:
            return

        if self.empresa_id != self.pedido.empresa_id:
            raise ValidationError(
                {"empresa": "La empresa debe coincidir con la empresa del pedido."}
            )
        if self.usuario_id != self.pedido.usuario_id:
            raise ValidationError(
                {"usuario": "El cliente debe coincidir con el cliente del pedido."}
            )
        if self.monto != self.pedido.total:
            raise ValidationError(
                {"monto": "El monto debe coincidir con el total historico del pedido."}
            )
        if self.moneda != self.pedido.moneda:
            raise ValidationError(
                {"moneda": "La moneda debe coincidir con la moneda del pedido."}
            )

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.empresa = self.pedido.empresa
            self.usuario = self.pedido.usuario
            self.monto = self.pedido.total
            self.moneda = self.pedido.moneda
            self.estado = self.Estado.PENDIENTE
        else:
            original = Pago.objects.get(pk=self.pk)
            if any(
                getattr(self, campo) != getattr(original, campo)
                for campo in self.CAMPOS_INMUTABLES
            ):
                raise ValidationError(
                    {"pago": "Los datos economicos del pago no pueden modificarse."}
                )
            if (
                self.estado != original.estado
                and not getattr(self, "_transicion_controlada", False)
            ):
                raise ValidationError(
                    {"estado": "El estado solo cambia mediante un webhook verificado."}
                )
            if (
                original.estado != self.Estado.PENDIENTE
                and self.estado != original.estado
            ):
                raise ValidationError(
                    {"estado": "Un resultado final de pago no puede modificarse."}
                )
            if original.estado != self.Estado.PENDIENTE and any(
                getattr(self, campo) != getattr(original, campo)
                for campo in self.CAMPOS_RESULTADO
            ):
                raise ValidationError(
                    {"pago": "El resultado confirmado del pago no puede modificarse."}
                )

        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.pk:
            raise ValidationError(
                {"pago": "Los intentos de pago se conservan como historial."}
            )
        return super().delete(*args, **kwargs)

    def cancelar_pendiente_administrativamente(self):
        if self.estado == self.Estado.CANCELADO:
            return False
        if self.estado != self.Estado.PENDIENTE:
            raise ValidationError(
                {"estado": "Solo se puede cancelar un intento pendiente."}
            )

        self.estado = self.Estado.CANCELADO
        self._transicion_controlada = True
        try:
            self.save(update_fields=["estado", "fecha_actualizacion"])
        finally:
            del self._transicion_controlada
        return True

    @classmethod
    def obtener_o_crear_pendiente(
        cls,
        pedido,
        proveedor,
        metodo=Metodo.EN_LINEA,
    ):
        with transaction.atomic():
            pedido = Pedido.objects.select_for_update().get(pk=pedido.pk)
            if pedido.estado_pago != Pedido.EstadoPago.PENDIENTE:
                raise ValidationError(
                    {"pedido": "Solo se puede iniciar el pago de un pedido pendiente."}
                )
            if pedido.total <= 0:
                raise ValidationError(
                    {"pedido": "El pedido no tiene un total valido para cobrar."}
                )
            if not pedido.detalles.exists():
                raise ValidationError(
                    {"pedido": "No se puede pagar un pedido sin detalles."}
                )

            existente = (
                cls.objects.select_for_update()
                .filter(pedido=pedido, estado=cls.Estado.PENDIENTE)
                .first()
            )
            if existente:
                if existente.metodo != metodo:
                    raise ValidationError(
                        {
                            "metodo": (
                                "El pedido ya tiene un pago pendiente con otro metodo."
                            )
                        }
                    )
                if metodo == cls.Metodo.SUCURSAL and existente.proveedor != proveedor:
                    raise ValidationError(
                        {
                            "proveedor": (
                                "El pago en sucursal pendiente tiene otro proveedor."
                            )
                        }
                    )
                return existente, False

            return cls.objects.create(
                pedido=pedido,
                proveedor=proveedor,
                metodo=metodo,
            ), True

    @classmethod
    def procesar_resultado(
        cls,
        referencia,
        proveedor,
        estado,
        identificador_externo,
        codigo_respuesta="",
    ):
        with transaction.atomic():
            pago = (
                cls.objects.select_for_update()
                .select_related("pedido", "empresa", "usuario")
                .get(referencia=referencia)
            )
            if pago.proveedor != proveedor:
                raise ValidationError(
                    {"proveedor": "El proveedor no coincide con el pago iniciado."}
                )
            if pago.estado != cls.Estado.PENDIENTE:
                if pago.estado == estado:
                    if (
                        pago.identificador_externo
                        and pago.identificador_externo != identificador_externo
                    ):
                        raise ValidationError(
                            {
                                "identificador_externo": (
                                    "El identificador no coincide con el resultado guardado."
                                )
                            }
                        )
                    return pago, False
                raise ValidationError(
                    {"estado": "Este pago ya tiene un resultado final diferente."}
                )

            if estado not in [cls.Estado.APROBADO, cls.Estado.RECHAZADO]:
                raise ValidationError(
                    {"estado": "El webhook debe aprobar o rechazar el pago."}
                )
            if (
                estado == cls.Estado.APROBADO
                and pago.pedido.estado_pago != Pedido.EstadoPago.PENDIENTE
            ):
                raise ValidationError(
                    {"pedido": "El pedido ya no esta disponible para este pago."}
                )

            pago.estado = estado
            pago.identificador_externo = identificador_externo
            pago.codigo_respuesta = codigo_respuesta
            pago.fecha_confirmacion = timezone.now()
            pago._transicion_controlada = True
            pago.save(
                update_fields=[
                    "estado",
                    "identificador_externo",
                    "codigo_respuesta",
                    "fecha_confirmacion",
                    "fecha_actualizacion",
                ]
            )

            if estado == cls.Estado.APROBADO:
                pago.pedido.estado_pago = Pedido.EstadoPago.PAGADO
                pago.pedido.save(
                    update_fields=["estado_pago", "fecha_actualizacion"]
                )

            return pago, True


class EventoWebhookPago(models.Model):
    pago = models.ForeignKey(
        Pago,
        on_delete=models.SET_NULL,
        related_name="eventos_webhook",
        null=True,
        blank=True,
    )
    proveedor = models.CharField(max_length=50)
    evento_id = models.CharField(max_length=150)
    referencia_pago = models.UUIDField()
    estado_recibido = models.CharField(max_length=20)
    hash_payload = models.CharField(max_length=64, editable=False)
    procesado = models.BooleanField(default=False)
    mensaje = models.CharField(max_length=250, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion", "-id"]
        verbose_name = "evento webhook de pago"
        verbose_name_plural = "eventos webhook de pagos"
        constraints = [
            models.UniqueConstraint(
                fields=["proveedor", "evento_id"],
                name="evento_pago_unico_por_proveedor",
            )
        ]

    def __str__(self):
        return f"{self.proveedor} - {self.evento_id}"

    def delete(self, *args, **kwargs):
        if self.pk:
            raise ValidationError(
                {"evento": "Los eventos webhook se conservan como auditoria."}
            )
        return super().delete(*args, **kwargs)
