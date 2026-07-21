import uuid
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction

from catalogo.models import Producto
from empresas.models import Empresa


ISV_RATE = Decimal("0.15")
MONEY_QUANTIZER = Decimal("0.01")


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
    )
    cantidad = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["producto__nombre"]
        verbose_name = "item de carrito"
        verbose_name_plural = "items de carrito"
        constraints = [
            models.UniqueConstraint(
                fields=["carrito", "producto"],
                name="item_carrito_producto_unico",
            )
        ]

    def __str__(self):
        return f"{self.producto} x {self.cantidad}"

    @property
    def subtotal(self):
        return self.precio_unitario * self.cantidad

    def clean(self):
        super().clean()

        if self.producto_id and self.carrito_id:
            if self.producto.empresa_id != self.carrito.empresa_id:
                raise ValidationError(
                    {"producto": "El producto debe pertenecer a la empresa del carrito."}
                )

            if self.cantidad > self.producto.existencia:
                raise ValidationError(
                    {"cantidad": "La cantidad no puede superar la existencia disponible."}
                )

    def save(self, *args, **kwargs):
        if not self.precio_unitario:
            self.precio_unitario = self.producto.precio

        super().save(*args, **kwargs)


class Pedido(models.Model):
    class TipoEntrega(models.TextChoices):
        RETIRO_EN_LOCAL = "retiro_en_local", "Retiro en local"
        ENVIO_LOCAL = "envio_local", "Envio local"
        ENVIO_NACIONAL = "envio_nacional", "Envio nacional"

    class EstadoPago(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        PAGADO = "pagado", "Pagado"

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
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    descuento_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    impuesto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    envio = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    moneda = models.CharField(max_length=3, default="HNL")
    observaciones = models.TextField(blank=True)
    inventario_descontado = models.BooleanField(default=False)
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

        debe_descontar_inventario = (
            self.pk
            and self.estado_pago == self.EstadoPago.PAGADO
            and not self.inventario_descontado
        )

        self._validar_tipo_entrega()
        self._validar_direccion_entrega()
        self.envio = self._obtener_monto_envio()
        self._calcular_totales()

        if not self.numero:
            self.numero = self._generar_numero()

        super().save(*args, **kwargs)

        if debe_descontar_inventario:
            self.descontar_inventario_por_pago()
            Prefactura.obtener_o_crear_para_pedido(self)

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
        self.impuesto = self._redondear_monto(base_imponible * ISV_RATE)
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
                pedido.detalles.select_related("producto").order_by("id")
            )

            if not detalles:
                raise ValidationError(
                    {"detalles": "No se puede descontar inventario de un pedido sin detalles."}
                )

            for detalle in detalles:
                MovimientoInventario.objects.create(
                    empresa=pedido.empresa,
                    producto=detalle.producto,
                    tipo=MovimientoInventario.Tipo.SALIDA,
                    cantidad=detalle.cantidad,
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
                ItemCarrito.objects.select_related("producto")
                .filter(carrito=carrito)
                .order_by("id")
            )

            if not items:
                raise ValidationError(
                    {"carrito": "No se puede generar un pedido con el carrito vacio."}
                )

            subtotal = Decimal("0.00")
            for item in items:
                if item.producto.empresa_id != carrito.empresa_id:
                    raise ValidationError(
                        {
                            "producto": (
                                "Todos los productos deben pertenecer a la empresa "
                                "del carrito."
                            )
                        }
                    )

                if item.cantidad > item.producto.existencia:
                    raise ValidationError(
                        {
                            "cantidad": (
                                f"El producto {item.producto.nombre} no tiene "
                                "existencia suficiente."
                            )
                        }
                    )

                subtotal += item.subtotal

            pedido = cls(
                empresa=carrito.empresa,
                usuario=carrito.usuario,
                carrito_origen=carrito,
                tipo_entrega=tipo_entrega,
                subtotal=subtotal,
                descuento_total=Decimal("0.00"),
                observaciones=observaciones,
                **(datos_entrega or {}),
            )
            pedido.full_clean()
            pedido.save()

            for item in items:
                DetallePedido.objects.create(
                    pedido=pedido,
                    producto=item.producto,
                    precio_unitario=item.precio_unitario,
                    cantidad=item.cantidad,
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
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name="detalles",
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name="detalles_pedido",
    )
    codigo_barra = models.CharField(max_length=80, editable=False)
    nombre_producto = models.CharField(max_length=180, editable=False)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, editable=False)

    class Meta:
        ordering = ["id"]
        verbose_name = "detalle de pedido"
        verbose_name_plural = "detalles de pedido"

    def __str__(self):
        return f"{self.nombre_producto} x {self.cantidad}"

    def clean(self):
        super().clean()

        if self.producto_id and self.pedido_id:
            if self.producto.empresa_id != self.pedido.empresa_id:
                raise ValidationError(
                    {"producto": "El producto debe pertenecer a la empresa del pedido."}
                )

    def save(self, *args, **kwargs):
        if not self.codigo_barra:
            self.codigo_barra = self.producto.codigo_barra

        if not self.nombre_producto:
            self.nombre_producto = self.producto.nombre

        if not self.precio_unitario:
            self.precio_unitario = self.producto.precio

        self.subtotal = self.precio_unitario * self.cantidad
        super().save(*args, **kwargs)


class Prefactura(models.Model):
    LEYENDA = (
        "Este documento corresponde a una prefactura y no representa una factura "
        "fiscal original."
    )

    pedido = models.OneToOneField(
        Pedido,
        on_delete=models.PROTECT,
        related_name="prefactura",
    )
    numero = models.CharField(max_length=30, unique=True, editable=False)
    leyenda = models.CharField(max_length=180, default=LEYENDA)
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
        if pedido.estado_pago != Pedido.EstadoPago.PAGADO:
            raise ValidationError(
                {"pedido": "Solo se puede generar prefactura para pedidos pagados."}
            )

        return cls.objects.get_or_create(
            pedido=pedido,
            defaults={"numero": cls.generar_numero(pedido)},
        )[0]

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
        if self.pedido_id and self.pedido.estado_pago != Pedido.EstadoPago.PAGADO:
            raise ValidationError(
                {"pedido": "Solo se puede generar prefactura para pedidos pagados."}
            )

    def save(self, *args, **kwargs):
        if not self.numero and self.pedido_id:
            self.numero = self.generar_numero(self.pedido)

        self.full_clean()
        super().save(*args, **kwargs)
