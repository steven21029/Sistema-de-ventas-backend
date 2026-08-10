import uuid
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.utils import timezone

from catalogo.models import PaqueteCatalogo, Producto
from empresas.models import Empresa, SucursalEmpresa


ISV_RATE = Decimal("0.15")
MONEY_QUANTIZER = Decimal("0.01")


def fecha_vencimiento_prefactura():
    return timezone.now() + timedelta(hours=settings.PREFACTURA_VIGENCIA_HORAS)


class Carrito(models.Model):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name="carritos",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="carritos",
    )
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_actualizacion"]
        verbose_name = "carrito"
        verbose_name_plural = "carritos"
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "usuario"],
                condition=models.Q(activo=True),
                name="carrito_activo_unico_por_usuario_empresa",
            )
        ]

    def __str__(self):
        return f"Carrito {self.usuario} - {self.empresa}"

    @property
    def total_items(self):
        return sum(item.cantidad for item in self.items.all())

    @property
    def subtotal(self):
        return sum(item.subtotal for item in self.items.all())


class ItemCarrito(models.Model):
    carrito = models.ForeignKey(
        Carrito,
        on_delete=models.CASCADE,
        related_name="items",
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name="items_carrito",
        blank=True,
        null=True,
    )
    paquete = models.ForeignKey(
        PaqueteCatalogo,
        on_delete=models.PROTECT,
        related_name="items_carrito",
        blank=True,
        null=True,
    )
    cantidad = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "item de carrito"
        verbose_name_plural = "items de carrito"
        constraints = [
            models.UniqueConstraint(
                fields=["carrito", "producto"],
                name="item_carrito_producto_unico",
            ),
            models.UniqueConstraint(
                fields=["carrito", "paquete"],
                name="item_carrito_paquete_unico",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(producto__isnull=False, paquete__isnull=True)
                    | models.Q(producto__isnull=True, paquete__isnull=False)
                ),
                name="item_carrito_un_solo_tipo_articulo",
            ),
        ]

    def __str__(self):
        return f"{self.articulo} x {self.cantidad}"

    @property
    def articulo(self):
        return self.producto or self.paquete

    @property
    def tipo_articulo(self):
        if self.producto_id:
            return "producto"

        return self.paquete.tipo if self.paquete_id else None

    @property
    def codigo_articulo(self):
        if self.producto_id:
            return self.producto.codigo_venta

        return self.paquete.codigo if self.paquete_id else None

    @property
    def nombre_articulo(self):
        return self.articulo.nombre if self.articulo else ""

    @property
    def controla_inventario(self):
        if self.producto_id:
            return self.producto.controla_inventario

        if self.paquete_id:
            return any(
                producto.controla_inventario
                for producto in self.paquete.productos.all()
            )

        return False

    @property
    def agotado(self):
        return self.articulo.agotado if self.articulo else False

    @property
    def subtotal(self):
        return self.precio_unitario * self.cantidad

    def clean(self):
        super().clean()

        if bool(self.producto_id) == bool(self.paquete_id):
            raise ValidationError(
                "El item debe tener un producto, perfil o combo, pero no varios."
            )

        if self.producto_id and self.carrito_id:
            if self.producto.empresa_id != self.carrito.empresa_id:
                raise ValidationError(
                    {"producto": "El producto debe pertenecer a la empresa del carrito."}
                )
            if (
                self.producto.controla_inventario
                and self.cantidad > self.producto.existencia
            ):
                raise ValidationError(
                    {"cantidad": "La cantidad no puede superar la existencia disponible."}
                )

        if self.paquete_id and self.carrito_id:
            if self.paquete.empresa_id != self.carrito.empresa_id:
                raise ValidationError(
                    {"paquete": "El perfil o combo debe pertenecer a la empresa del carrito."}
                )

            for componente in self.paquete.items_productos.select_related(
                "producto"
            ):
                producto = componente.producto
                if (
                    producto.controla_inventario
                    and self.cantidad * componente.cantidad > producto.existencia
                ):
                    raise ValidationError(
                        {
                            "cantidad": (
                                f"El paquete {self.paquete.nombre} no tiene "
                                f"existencia suficiente de {producto.nombre}."
                            )
                        }
                    )

    def save(self, *args, **kwargs):
        if not self.precio_unitario:
            self.precio_unitario = (
                self.producto.precio
                if self.producto_id
                else self.paquete.precio_paquete
            )

        self.full_clean()
        super().save(*args, **kwargs)


class Pedido(models.Model):
    CAMPOS_FOTOGRAFIA = (
        "empresa_id",
        "usuario_id",
        "carrito_origen_id",
        "numero",
        "tipo_entrega",
        "nombre_recibe",
        "telefono_recibe",
        "direccion_entrega",
        "referencia_entrega",
        "departamento_entrega",
        "municipio_entrega",
        "subtotal",
        "descuento_total",
        "impuesto",
        "aplica_impuesto",
        "tasa_impuesto",
        "envio",
        "total",
        "moneda",
        "observaciones",
    )

    class TipoEntrega(models.TextChoices):
        RETIRO_EN_LOCAL = "retiro_en_local", "Retiro en local"
        ENVIO_LOCAL = "envio_local", "Envio local"
        ENVIO_NACIONAL = "envio_nacional", "Envio nacional"

    class EstadoPago(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        PAGADO = "pagado", "Pagado"
        CANCELADO = "cancelado", "Cancelado"

    class MetodoPago(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente de seleccion"
        EN_LINEA = "en_linea", "Pago en linea"
        SUCURSAL = "sucursal", "Pago en sucursal"

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name="pedidos",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="pedidos",
    )
    carrito_origen = models.OneToOneField(
        Carrito,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pedido",
    )
    numero = models.CharField(max_length=20, unique=True, editable=False)
    tipo_entrega = models.CharField(
        max_length=30,
        choices=TipoEntrega.choices,
        default=TipoEntrega.RETIRO_EN_LOCAL,
    )
    nombre_recibe = models.CharField(max_length=180, blank=True)
    telefono_recibe = models.CharField(max_length=30, blank=True)
    direccion_entrega = models.TextField(blank=True)
    referencia_entrega = models.TextField(blank=True)
    departamento_entrega = models.CharField(max_length=120, blank=True)
    municipio_entrega = models.CharField(max_length=120, blank=True)
    estado_pago = models.CharField(
        max_length=20,
        choices=EstadoPago.choices,
        default=EstadoPago.PENDIENTE,
    )
    metodo_pago = models.CharField(
        max_length=20,
        choices=MetodoPago.choices,
        default=MetodoPago.PENDIENTE,
    )
    sucursal_pago = models.ForeignKey(
        SucursalEmpresa,
        on_delete=models.PROTECT,
        related_name="pedidos_pago_sucursal",
        null=True,
        blank=True,
    )
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    descuento_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    impuesto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    aplica_impuesto = models.BooleanField(default=True, editable=False)
    tasa_impuesto = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=ISV_RATE,
        editable=False,
    )
    envio = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    moneda = models.CharField(max_length=3, default="HNL")
    observaciones = models.TextField(blank=True)
    inventario_descontado = models.BooleanField(default=False)
    motivo_cancelacion = models.TextField(blank=True)
    cancelado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="pedidos_cancelados_administrativamente",
        null=True,
        blank=True,
        editable=False,
    )
    fecha_cancelacion = models.DateTimeField(null=True, blank=True, editable=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion", "-id"]
        verbose_name = "pedido"
        verbose_name_plural = "pedidos"

    def __str__(self):
        return f"Pedido {self.numero}"

    def clean(self):
        super().clean()
        self._validar_metodo_pago()
        if self.pk:
            try:
                original = Pedido.objects.get(pk=self.pk)
            except Pedido.DoesNotExist:
                pass
            else:
                self._validar_fotografia_inmutable(original)
                return

        self._validar_tipo_entrega()
        self._validar_direccion_entrega()
        self._obtener_monto_envio()
        self._validar_descuento()

    def save(self, *args, **kwargs):
        update_fields = kwargs.get("update_fields")
        if update_fields and set(update_fields).issubset(
            {"inventario_descontado", "fecha_actualizacion"}
        ):
            super().save(*args, **kwargs)
            return

        if self._state.adding:
            if self.empresa_id:
                self.aplica_impuesto = self.empresa.cobra_impuesto
                self.tasa_impuesto = (
                    ISV_RATE if self.aplica_impuesto else Decimal("0.0000")
                )

            self._validar_tipo_entrega()
            self._validar_direccion_entrega()
            self.envio = self._obtener_monto_envio()
            self._calcular_totales()

            if not self.numero:
                self.numero = self._generar_numero()

            super().save(*args, **kwargs)
            return

        with transaction.atomic():
            original = Pedido.objects.select_for_update().get(pk=self.pk)
            self._validar_fotografia_inmutable(original)
            debe_descontar_inventario = (
                original.estado_pago == self.EstadoPago.PENDIENTE
                and self.estado_pago == self.EstadoPago.PAGADO
                and not original.inventario_descontado
            )

            super().save(*args, **kwargs)

            if debe_descontar_inventario:
                self.descontar_inventario_por_pago()
                Prefactura.obtener_o_crear_para_pedido(self)

    def _validar_fotografia_inmutable(self, original):
        modificados = [
            campo
            for campo in self.CAMPOS_FOTOGRAFIA
            if getattr(self, campo) != getattr(original, campo)
        ]
        if modificados:
            raise ValidationError(
                {
                    "pedido": (
                        "La fotografia comercial del pedido no puede modificarse "
                        "despues del checkout."
                    )
                }
            )

        if self.inventario_descontado != original.inventario_descontado:
            raise ValidationError(
                {
                    "inventario_descontado": (
                        "Este estado se actualiza automaticamente al confirmar el pago."
                    )
                }
            )

        cancelacion_modificada = (
            self.motivo_cancelacion != original.motivo_cancelacion
            or self.cancelado_por_id != original.cancelado_por_id
            or self.fecha_cancelacion != original.fecha_cancelacion
        )
        if cancelacion_modificada and not getattr(
            self,
            "_cancelacion_administrativa_controlada",
            False,
        ):
            raise ValidationError(
                {"cancelacion": "La cancelacion solo se registra mediante su flujo."}
            )

        metodo_modificado = (
            self.metodo_pago != original.metodo_pago
            or self.sucursal_pago_id != original.sucursal_pago_id
        )
        if metodo_modificado:
            if not getattr(self, "_seleccion_metodo_controlada", False):
                raise ValidationError(
                    {"metodo_pago": "El metodo de pago solo cambia mediante su flujo."}
                )
            if original.metodo_pago != self.MetodoPago.PENDIENTE:
                raise ValidationError(
                    {"metodo_pago": "El metodo de pago seleccionado no puede cambiar."}
                )

        self._validar_metodo_pago()

        estados_validos = {opcion for opcion, _nombre in self.EstadoPago.choices}
        if self.estado_pago not in estados_validos:
            raise ValidationError({"estado_pago": "El estado de pago no es valido."})

        if (
            original.estado_pago == self.EstadoPago.PAGADO
            and self.estado_pago != self.EstadoPago.PAGADO
        ):
            raise ValidationError(
                {"estado_pago": "Un pedido pagado no puede volver a pendiente."}
            )

    def _validar_metodo_pago(self):
        if self.metodo_pago == self.MetodoPago.SUCURSAL:
            if not self.sucursal_pago_id:
                raise ValidationError(
                    {"sucursal_pago": "Selecciona la sucursal donde se pagara."}
                )
            if self.empresa_id != self.sucursal_pago.empresa_id:
                raise ValidationError(
                    {"sucursal_pago": "La sucursal debe pertenecer a la empresa."}
                )
            return

        if self.sucursal_pago_id:
            raise ValidationError(
                {"sucursal_pago": "Solo el pago en sucursal admite una sucursal."}
            )

    def seleccionar_metodo_pago(self, metodo, sucursal=None):
        if self.estado_pago != self.EstadoPago.PENDIENTE:
            raise ValidationError(
                {"estado_pago": "Solo un pedido pendiente puede elegir metodo de pago."}
            )
        if metodo not in {
            self.MetodoPago.EN_LINEA,
            self.MetodoPago.SUCURSAL,
        }:
            raise ValidationError({"metodo_pago": "El metodo de pago no es valido."})
        if self.metodo_pago not in {self.MetodoPago.PENDIENTE, metodo}:
            raise ValidationError(
                {"metodo_pago": "El pedido ya tiene otro metodo de pago seleccionado."}
            )

        sucursal_id = sucursal.pk if sucursal else None
        if self.metodo_pago == metodo:
            if self.sucursal_pago_id != sucursal_id:
                raise ValidationError(
                    {"sucursal_pago": "El pedido ya tiene otra sucursal seleccionada."}
                )
            return False

        self.metodo_pago = metodo
        self.sucursal_pago = sucursal
        self._seleccion_metodo_controlada = True
        try:
            self.save(
                update_fields=[
                    "metodo_pago",
                    "sucursal_pago",
                    "fecha_actualizacion",
                ]
            )
        finally:
            del self._seleccion_metodo_controlada
        return True

    def cancelar_pendiente_administrativamente(self, administrador, motivo):
        if (
            self.estado_pago == self.EstadoPago.CANCELADO
            and self.fecha_cancelacion
            and self.cancelado_por_id
        ):
            return False
        if self.estado_pago != self.EstadoPago.PENDIENTE:
            raise ValidationError(
                {"estado_pago": "Solo se puede cancelar un pedido pendiente."}
            )
        if self.inventario_descontado:
            raise ValidationError(
                {"inventario": "El pedido ya tiene efectos de inventario."}
            )

        motivo = str(motivo).strip()
        if not motivo:
            raise ValidationError({"motivo": "El motivo es obligatorio."})

        self.estado_pago = self.EstadoPago.CANCELADO
        self.motivo_cancelacion = motivo
        self.cancelado_por = administrador
        self.fecha_cancelacion = timezone.now()
        self._cancelacion_administrativa_controlada = True
        try:
            self.save(
                update_fields=[
                    "estado_pago",
                    "motivo_cancelacion",
                    "cancelado_por",
                    "fecha_cancelacion",
                    "fecha_actualizacion",
                ]
            )
        finally:
            del self._cancelacion_administrativa_controlada
        return True

    def delete(self, *args, **kwargs):
        if self.pk:
            raise ValidationError(
                {"pedido": "Los pedidos confirmados se conservan como historial."}
            )
        return super().delete(*args, **kwargs)

    def _validar_tipo_entrega(self):
        if not self.empresa_id:
            return

        if self.empresa.tiene_envios:
            opciones_validas = [
                self.TipoEntrega.ENVIO_LOCAL,
                self.TipoEntrega.ENVIO_NACIONAL,
            ]
            if self.tipo_entrega not in opciones_validas:
                raise ValidationError(
                    {
                        "tipo_entrega": (
                            "Esta empresa tiene envios; debe seleccionar envio local "
                            "o envio nacional."
                        )
                    }
                )
            return

        if self.tipo_entrega != self.TipoEntrega.RETIRO_EN_LOCAL:
            raise ValidationError(
                {
                    "tipo_entrega": (
                        "Esta empresa no tiene envios; solo permite retiro en local."
                    )
                }
            )

    def _validar_direccion_entrega(self):
        if self.tipo_entrega == self.TipoEntrega.RETIRO_EN_LOCAL:
            return

        campos_requeridos = {
            "nombre_recibe": self.nombre_recibe,
            "telefono_recibe": self.telefono_recibe,
            "direccion_entrega": self.direccion_entrega,
            "departamento_entrega": self.departamento_entrega,
            "municipio_entrega": self.municipio_entrega,
        }
        errores = {
            campo: "Este campo es obligatorio para envios."
            for campo, valor in campos_requeridos.items()
            if not str(valor).strip()
        }
        if errores:
            raise ValidationError(errores)

    def _validar_descuento(self):
        if self.descuento_total > self.subtotal:
            raise ValidationError(
                {"descuento_total": "El descuento no puede ser mayor al subtotal."}
            )

    def _obtener_monto_envio(self):
        if not self.empresa_id:
            return Decimal("0.00")

        if self.tipo_entrega == self.TipoEntrega.RETIRO_EN_LOCAL:
            return Decimal("0.00")

        tarifa = TarifaEntrega.objects.filter(
            empresa_id=self.empresa_id,
            tipo_entrega=self.tipo_entrega,
            activa=True,
        ).first()

        if not tarifa:
            raise ValidationError(
                {
                    "envio": (
                        "No hay una tarifa activa configurada para este tipo de entrega."
                    )
                }
            )

        return tarifa.monto

    def _calcular_totales(self):
        self._validar_descuento()

        base_imponible = self.subtotal - self.descuento_total
        tasa = self.tasa_impuesto if self.aplica_impuesto else Decimal("0.0000")
        self.impuesto = self._redondear_monto(base_imponible * tasa)
        self.total = self._redondear_monto(base_imponible + self.impuesto + self.envio)

    def _redondear_monto(self, monto):
        return monto.quantize(MONEY_QUANTIZER, rounding=ROUND_HALF_UP)

    def _generar_numero(self):
        while True:
            numero = uuid.uuid4().hex[:12].upper()
            if not Pedido.objects.filter(numero=numero).exists():
                return numero

    def descontar_inventario_por_pago(self):
        from inventario.models import MovimientoInventario

        with transaction.atomic():
            pedido = (
                Pedido.objects.select_for_update()
                .select_related("empresa", "usuario")
                .get(pk=self.pk)
            )

            if pedido.inventario_descontado:
                return

            if pedido.estado_pago != self.EstadoPago.PAGADO:
                raise ValidationError(
                    {"estado_pago": "Solo se descuenta inventario en pedidos pagados."}
                )

            detalles = list(
                pedido.detalles.select_related(
                    "producto",
                    "paquete",
                )
                .prefetch_related("componentes__producto")
                .order_by("id")
            )

            if not detalles:
                raise ValidationError(
                    {"detalles": "No se puede descontar inventario de un pedido sin detalles."}
                )

            salidas = {}
            for detalle in detalles:
                if detalle.producto_id:
                    componentes = [(detalle.producto, detalle.cantidad)]
                else:
                    componentes = [
                        (
                            componente.producto,
                            detalle.cantidad * componente.cantidad_por_unidad,
                        )
                        for componente in detalle.componentes.all()
                    ]

                for producto, cantidad in componentes:
                    if not producto.controla_inventario:
                        continue
                    if producto.pk not in salidas:
                        salidas[producto.pk] = {
                            "producto": producto,
                            "cantidad": 0,
                        }
                    salidas[producto.pk]["cantidad"] += cantidad

            for salida in salidas.values():
                MovimientoInventario.objects.create(
                    empresa=pedido.empresa,
                    producto=salida["producto"],
                    tipo=MovimientoInventario.Tipo.SALIDA,
                    cantidad=salida["cantidad"],
                    motivo=f"Pedido pagado {pedido.numero}",
                    referencia=pedido.numero,
                    usuario=pedido.usuario,
                )

            pedido.inventario_descontado = True
            pedido.save(update_fields=["inventario_descontado", "fecha_actualizacion"])
            self.inventario_descontado = True

    @classmethod
    def generar_desde_carrito(
        cls,
        carrito,
        tipo_entrega,
        observaciones="",
        datos_entrega=None,
    ):
        with transaction.atomic():
            carrito = (
                Carrito.objects.select_for_update()
                .select_related("empresa", "usuario")
                .get(pk=carrito.pk)
            )

            if not carrito.activo:
                raise ValidationError({"carrito": "Este carrito ya no esta activo."})

            if hasattr(carrito, "pedido"):
                raise ValidationError(
                    {"carrito": "Este carrito ya fue convertido en pedido."}
                )

            items = list(
                ItemCarrito.objects.select_related(
                    "producto",
                    "paquete",
                )
                .prefetch_related("paquete__items_productos__producto")
                .filter(carrito=carrito)
                .order_by("id")
            )

            if not items:
                raise ValidationError(
                    {"carrito": "No se puede generar un pedido con el carrito vacio."}
                )

            inventario_requerido = {}
            for item in items:
                if item.producto_id:
                    articulo = item.producto
                    if articulo.empresa_id != carrito.empresa_id:
                        raise ValidationError(
                            {
                                "producto": (
                                    "Todos los productos deben pertenecer a la empresa "
                                    "del carrito."
                                )
                            }
                        )
                    if not articulo.activo:
                        raise ValidationError(
                            {
                                "producto": (
                                    f"El articulo {articulo.nombre} ya no esta activo."
                                )
                            }
                        )
                    componentes = [(articulo, item.cantidad)]
                else:
                    articulo = item.paquete
                    if articulo.empresa_id != carrito.empresa_id:
                        raise ValidationError(
                            {
                                "paquete": (
                                    "Todos los perfiles y combos deben pertenecer "
                                    "a la empresa del carrito."
                                )
                            }
                        )
                    if not articulo.activo:
                        raise ValidationError(
                            {
                                "paquete": (
                                    f"El articulo {articulo.nombre} ya no esta activo."
                                )
                            }
                        )
                    componentes = []
                    for componente in articulo.items_productos.all():
                        producto = componente.producto
                        if not producto.activo:
                            raise ValidationError(
                                {
                                    "paquete": (
                                        f"El componente {producto.nombre} del paquete "
                                        "ya no esta activo."
                                    )
                                }
                            )
                        componentes.append(
                            (producto, item.cantidad * componente.cantidad)
                        )

                for producto, cantidad in componentes:
                    if not producto.controla_inventario:
                        continue
                    if producto.pk not in inventario_requerido:
                        inventario_requerido[producto.pk] = {
                            "producto": producto,
                            "cantidad": 0,
                        }
                    inventario_requerido[producto.pk]["cantidad"] += cantidad

            for requerido in inventario_requerido.values():
                producto = requerido["producto"]
                if requerido["cantidad"] > producto.existencia:
                    raise ValidationError(
                        {
                            "cantidad": (
                                f"El articulo {producto.nombre} no tiene "
                                "existencia suficiente para completar el carrito."
                            )
                        }
                    )

            from .services import calcular_carrito

            calculo = calcular_carrito(
                carrito.empresa,
                [
                    {
                        "producto": item.producto,
                        "paquete": item.paquete,
                        "cantidad": item.cantidad,
                    }
                    for item in items
                ],
            )

            pedido = cls(
                empresa=carrito.empresa,
                usuario=carrito.usuario,
                carrito_origen=carrito,
                tipo_entrega=tipo_entrega,
                subtotal=calculo["subtotal"],
                descuento_total=calculo["descuento_total"],
                observaciones=observaciones,
                **(datos_entrega or {}),
            )
            pedido.full_clean()
            pedido.save()

            for linea in calculo["lineas"]:
                detalle = DetallePedido.objects.create(
                    pedido=pedido,
                    producto=linea["producto"],
                    paquete=linea["paquete"],
                    precio_unitario=linea["precio_unitario"],
                    cantidad=linea["cantidad"],
                    descuento_promocional=linea["descuento"],
                    porcentaje_descuento=linea["porcentaje_descuento"],
                )
                if linea["paquete"]:
                    for componente in linea["paquete"].items_productos.all():
                        DetallePedidoComponente.objects.create(
                            detalle=detalle,
                            producto=componente.producto,
                            cantidad_por_unidad=componente.cantidad,
                        )

            carrito.activo = False
            carrito.save(update_fields=["activo", "fecha_actualizacion"])

            return pedido


class TarifaEntrega(models.Model):
    class TipoEntrega(models.TextChoices):
        ENVIO_LOCAL = Pedido.TipoEntrega.ENVIO_LOCAL, "Envio local"
        ENVIO_NACIONAL = Pedido.TipoEntrega.ENVIO_NACIONAL, "Envio nacional"

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name="tarifas_entrega",
    )
    tipo_entrega = models.CharField(max_length=30, choices=TipoEntrega.choices)
    monto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["empresa__nombre", "tipo_entrega"]
        verbose_name = "tarifa de entrega"
        verbose_name_plural = "tarifas de entrega"
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "tipo_entrega"],
                name="tarifa_entrega_unica_por_empresa_tipo",
            )
        ]

    def __str__(self):
        return f"{self.empresa} - {self.get_tipo_entrega_display()} - L {self.monto}"

    def clean(self):
        super().clean()

        if self.empresa_id and not self.empresa.tiene_envios:
            raise ValidationError(
                {
                    "empresa": (
                        "Esta empresa no tiene envios activos; no debe tener tarifas "
                        "de envio."
                    )
                }
            )


class DetallePedido(models.Model):
    CAMPOS_FOTOGRAFIA = (
        "pedido_id",
        "producto_id",
        "paquete_id",
        "tipo_articulo",
        "codigo_articulo",
        "nombre_articulo",
        "codigo_interno",
        "codigo_barra",
        "nombre_producto",
        "precio_unitario",
        "cantidad",
        "subtotal",
        "descuento_promocional_id",
        "promocion_codigo",
        "promocion_titulo",
        "porcentaje_descuento",
        "descuento_unitario",
        "precio_unitario_final",
        "descuento_total",
        "subtotal_final",
    )

    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name="detalles",
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name="detalles_pedido",
        blank=True,
        null=True,
    )
    paquete = models.ForeignKey(
        PaqueteCatalogo,
        on_delete=models.PROTECT,
        related_name="detalles_pedido",
        blank=True,
        null=True,
    )
    tipo_articulo = models.CharField(
        max_length=20,
        default="producto",
        editable=False,
    )
    codigo_articulo = models.CharField(
        max_length=80,
        blank=True,
        editable=False,
    )
    nombre_articulo = models.CharField(
        max_length=180,
        blank=True,
        editable=False,
    )
    codigo_interno = models.CharField(max_length=80, editable=False)
    codigo_barra = models.CharField(
        max_length=80,
        editable=False,
        null=True,
        blank=True,
    )
    nombre_producto = models.CharField(max_length=180, editable=False)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    descuento_promocional = models.ForeignKey(
        "promociones.DescuentoPromocional",
        on_delete=models.SET_NULL,
        related_name="detalles_pedido",
        null=True,
        blank=True,
        editable=False,
    )
    promocion_codigo = models.CharField(max_length=80, blank=True, editable=False)
    promocion_titulo = models.CharField(max_length=160, blank=True, editable=False)
    porcentaje_descuento = models.PositiveSmallIntegerField(
        default=0,
        validators=[MaxValueValidator(99)],
        editable=False,
    )
    descuento_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        editable=False,
    )
    precio_unitario_final = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        editable=False,
    )
    descuento_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        editable=False,
    )
    subtotal_final = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        editable=False,
    )

    class Meta:
        ordering = ["id"]
        verbose_name = "detalle de pedido"
        verbose_name_plural = "detalles de pedido"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(producto__isnull=False, paquete__isnull=True)
                    | models.Q(producto__isnull=True, paquete__isnull=False)
                ),
                name="detalle_pedido_un_solo_tipo_articulo",
            )
        ]

    def __str__(self):
        return f"{self.nombre_articulo or self.nombre_producto} x {self.cantidad}"

    @property
    def articulo(self):
        return self.producto or self.paquete

    def clean(self):
        super().clean()

        if bool(self.producto_id) == bool(self.paquete_id):
            raise ValidationError(
                "El detalle debe tener un producto, perfil o combo, pero no varios."
            )

        if self.producto_id and self.pedido_id:
            if self.producto.empresa_id != self.pedido.empresa_id:
                raise ValidationError(
                    {"producto": "El producto debe pertenecer a la empresa del pedido."}
                )

        if self.paquete_id and self.pedido_id:
            if self.paquete.empresa_id != self.pedido.empresa_id:
                raise ValidationError(
                    {"paquete": "El perfil o combo debe pertenecer a la empresa del pedido."}
                )

    def save(self, *args, **kwargs):
        if self.pk:
            original = DetallePedido.objects.get(pk=self.pk)
            if any(
                getattr(self, campo) != getattr(original, campo)
                for campo in self.CAMPOS_FOTOGRAFIA
            ):
                raise ValidationError(
                    {
                        "detalle": (
                            "La fotografia del articulo comprado no puede modificarse."
                        )
                    }
                )
            return super().save(*args, **kwargs)

        if self.producto_id:
            self.tipo_articulo = "producto"
            if not self.codigo_articulo:
                self.codigo_articulo = self.producto.codigo_venta
            if not self.nombre_articulo:
                self.nombre_articulo = self.producto.nombre
            if not self.codigo_interno:
                self.codigo_interno = self.producto.codigo_interno
            if not self.codigo_barra:
                self.codigo_barra = self.producto.codigo_barra
            if not self.nombre_producto:
                self.nombre_producto = self.producto.nombre
            if not self.precio_unitario:
                self.precio_unitario = self.producto.precio
        elif self.paquete_id:
            self.tipo_articulo = self.paquete.tipo
            if not self.codigo_articulo:
                self.codigo_articulo = self.paquete.codigo
            if not self.nombre_articulo:
                self.nombre_articulo = self.paquete.nombre
            if not self.codigo_interno:
                self.codigo_interno = self.paquete.codigo
            if not self.nombre_producto:
                self.nombre_producto = self.paquete.nombre
            if not self.precio_unitario:
                self.precio_unitario = self.paquete.precio_paquete

        if self.descuento_promocional_id:
            if not self.promocion_codigo:
                self.promocion_codigo = self.descuento_promocional.codigo
            if not self.promocion_titulo:
                self.promocion_titulo = self.descuento_promocional.titulo

        porcentaje = Decimal(self.porcentaje_descuento) / Decimal("100")
        self.descuento_unitario = (
            self.precio_unitario * porcentaje
        ).quantize(MONEY_QUANTIZER, rounding=ROUND_HALF_UP)
        self.precio_unitario_final = self.precio_unitario - self.descuento_unitario
        self.subtotal = self.precio_unitario * self.cantidad
        self.descuento_total = self.descuento_unitario * self.cantidad
        self.subtotal_final = self.precio_unitario_final * self.cantidad
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.pk:
            raise ValidationError(
                {"detalle": "Los detalles comprados se conservan como historial."}
            )
        return super().delete(*args, **kwargs)


class DetallePedidoComponente(models.Model):
    CAMPOS_FOTOGRAFIA = (
        "detalle_id",
        "producto_id",
        "codigo_interno",
        "codigo_barra",
        "nombre_producto",
        "cantidad_por_unidad",
    )

    detalle = models.ForeignKey(
        DetallePedido,
        on_delete=models.CASCADE,
        related_name="componentes",
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name="componentes_pedido",
    )
    codigo_interno = models.CharField(max_length=80, editable=False)
    codigo_barra = models.CharField(
        max_length=80,
        editable=False,
        null=True,
        blank=True,
    )
    nombre_producto = models.CharField(max_length=180, editable=False)
    cantidad_por_unidad = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )

    class Meta:
        ordering = ["id"]
        verbose_name = "componente de detalle de pedido"
        verbose_name_plural = "componentes de detalles de pedido"
        constraints = [
            models.UniqueConstraint(
                fields=["detalle", "producto"],
                name="detalle_pedido_componente_unico",
            )
        ]

    def __str__(self):
        return f"{self.nombre_producto} - {self.detalle}"

    def clean(self):
        super().clean()
        if self.detalle_id and not self.detalle.paquete_id:
            raise ValidationError(
                {"detalle": "Solo los perfiles y combos admiten componentes."}
            )

        if (
            self.detalle_id
            and self.producto_id
            and self.detalle.pedido.empresa_id != self.producto.empresa_id
        ):
            raise ValidationError(
                {"producto": "El componente debe pertenecer a la empresa del pedido."}
            )

    def save(self, *args, **kwargs):
        if self.pk:
            original = DetallePedidoComponente.objects.get(pk=self.pk)
            if any(
                getattr(self, campo) != getattr(original, campo)
                for campo in self.CAMPOS_FOTOGRAFIA
            ):
                raise ValidationError(
                    {
                        "componente": (
                            "La fotografia del componente comprado no puede modificarse."
                        )
                    }
                )
            return super().save(*args, **kwargs)

        if not self.codigo_interno:
            self.codigo_interno = self.producto.codigo_interno
        if not self.codigo_barra:
            self.codigo_barra = self.producto.codigo_barra
        if not self.nombre_producto:
            self.nombre_producto = self.producto.nombre

        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.pk:
            raise ValidationError(
                {"componente": "Los componentes comprados se conservan como historial."}
            )
        return super().delete(*args, **kwargs)


class Prefactura(models.Model):
    LEYENDA = "PREFACTURA - NO ES COMPROBANTE FISCAL"

    pedido = models.OneToOneField(
        Pedido,
        on_delete=models.PROTECT,
        related_name="prefactura",
    )
    numero = models.CharField(max_length=30, unique=True, editable=False)
    leyenda = models.CharField(max_length=180, default=LEYENDA)
    fecha_vencimiento = models.DateTimeField(default=fecha_vencimiento_prefactura)
    intentos_correo = models.PositiveSmallIntegerField(default=0)
    fecha_ultimo_intento_correo = models.DateTimeField(null=True, blank=True)
    correo_enviado_en = models.DateTimeField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion", "-id"]
        verbose_name = "prefactura"
        verbose_name_plural = "prefacturas"

    def __str__(self):
        return f"Prefactura {self.numero}"

    @classmethod
    def obtener_o_crear_para_pedido(cls, pedido):
        if not cls.puede_generarse_para(pedido):
            raise ValidationError(
                {
                    "pedido": (
                        "La prefactura requiere un pedido pagado o un pago "
                        "pendiente en sucursal."
                    )
                }
            )

        return cls.objects.get_or_create(
            pedido=pedido,
            defaults={"numero": cls.generar_numero(pedido)},
        )[0]

    @classmethod
    def puede_generarse_para(cls, pedido):
        return pedido.estado_pago == Pedido.EstadoPago.PAGADO or (
            pedido.estado_pago == Pedido.EstadoPago.PENDIENTE
            and pedido.metodo_pago == Pedido.MetodoPago.SUCURSAL
            and pedido.sucursal_pago_id
        )

    @classmethod
    def generar_numero(cls, pedido):
        base = f"PF-{pedido.numero}"
        if not cls.objects.filter(numero=base).exists():
            return base

        contador = 2
        while True:
            numero = f"{base}-{contador}"
            if not cls.objects.filter(numero=numero).exists():
                return numero

            contador += 1

    def clean(self):
        super().clean()
        if self.pedido_id and not self.puede_generarse_para(self.pedido):
            raise ValidationError(
                {
                    "pedido": (
                        "La prefactura requiere un pedido pagado o un pago "
                        "pendiente en sucursal."
                    )
                }
            )

    def save(self, *args, **kwargs):
        if not self.numero and self.pedido_id:
            self.numero = self.generar_numero(self.pedido)

        self.full_clean()
        super().save(*args, **kwargs)
