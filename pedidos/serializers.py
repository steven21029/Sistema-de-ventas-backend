from rest_framework import serializers

from .models import Carrito, DetallePedido, ItemCarrito, Pedido, Prefactura, TarifaEntrega


class ItemCarritoSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)
    codigo_barra = serializers.CharField(source="producto.codigo_barra", read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = ItemCarrito
        fields = [
            "id",
            "carrito",
            "producto",
            "producto_nombre",
            "codigo_barra",
            "cantidad",
            "precio_unitario",
            "subtotal",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id",
            "producto_nombre",
            "codigo_barra",
            "precio_unitario",
            "subtotal",
            "fecha_creacion",
            "fecha_actualizacion",
        ]

    def validate(self, attrs):
        carrito = attrs.get("carrito") or getattr(self.instance, "carrito", None)
        producto = attrs.get("producto") or getattr(self.instance, "producto", None)
        cantidad = attrs.get("cantidad") or getattr(self.instance, "cantidad", 1)

        if carrito and producto and carrito.empresa_id != producto.empresa_id:
            raise serializers.ValidationError(
                {"producto": "El producto debe pertenecer a la empresa del carrito."}
            )

        if producto and cantidad > producto.existencia:
            raise serializers.ValidationError(
                {"cantidad": "La cantidad no puede superar la existencia disponible."}
            )

        return attrs


class CarritoSerializer(serializers.ModelSerializer):
    items = ItemCarritoSerializer(many=True, read_only=True)
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    usuario_nombre = serializers.CharField(source="usuario.username", read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Carrito
        fields = [
            "id",
            "empresa",
            "empresa_nombre",
            "usuario",
            "usuario_nombre",
            "activo",
            "total_items",
            "subtotal",
            "items",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id",
            "empresa_nombre",
            "usuario_nombre",
            "total_items",
            "subtotal",
            "items",
            "fecha_creacion",
            "fecha_actualizacion",
        ]


class DetallePedidoSerializer(serializers.ModelSerializer):
    producto_nombre_actual = serializers.CharField(source="producto.nombre", read_only=True)

    class Meta:
        model = DetallePedido
        fields = [
            "id",
            "pedido",
            "producto",
            "producto_nombre_actual",
            "codigo_barra",
            "nombre_producto",
            "precio_unitario",
            "cantidad",
            "subtotal",
        ]
        read_only_fields = [
            "id",
            "producto_nombre_actual",
            "codigo_barra",
            "nombre_producto",
            "subtotal",
        ]

    def validate(self, attrs):
        pedido = attrs.get("pedido") or getattr(self.instance, "pedido", None)
        producto = attrs.get("producto") or getattr(self.instance, "producto", None)

        if pedido and producto and pedido.empresa_id != producto.empresa_id:
            raise serializers.ValidationError(
                {"producto": "El producto debe pertenecer a la empresa del pedido."}
            )

        return attrs


class PedidoSerializer(serializers.ModelSerializer):
    detalles = DetallePedidoSerializer(many=True, read_only=True)
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    usuario_nombre = serializers.CharField(source="usuario.username", read_only=True)

    class Meta:
        model = Pedido
        fields = [
            "id",
            "empresa",
            "empresa_nombre",
            "usuario",
            "usuario_nombre",
            "carrito_origen",
            "numero",
            "tipo_entrega",
            "estado_pago",
            "subtotal",
            "descuento_total",
            "impuesto",
            "envio",
            "total",
            "moneda",
            "observaciones",
            "inventario_descontado",
            "detalles",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id",
            "empresa_nombre",
            "usuario_nombre",
            "numero",
            "estado_pago",
            "impuesto",
            "envio",
            "total",
            "inventario_descontado",
            "detalles",
            "fecha_creacion",
            "fecha_actualizacion",
        ]

    def validate(self, attrs):
        empresa = attrs.get("empresa") or getattr(self.instance, "empresa", None)
        carrito = attrs.get("carrito_origen") or getattr(self.instance, "carrito_origen", None)
        tipo_entrega = attrs.get("tipo_entrega") or getattr(
            self.instance,
            "tipo_entrega",
            Pedido.TipoEntrega.RETIRO_EN_LOCAL,
        )
        subtotal = attrs.get("subtotal") or getattr(self.instance, "subtotal", 0)
        descuento_total = attrs.get("descuento_total") or getattr(
            self.instance,
            "descuento_total",
            0,
        )

        if empresa and carrito and empresa != carrito.empresa:
            raise serializers.ValidationError(
                {"carrito_origen": "El carrito debe pertenecer a la empresa del pedido."}
            )

        if descuento_total > subtotal:
            raise serializers.ValidationError(
                {"descuento_total": "El descuento no puede ser mayor al subtotal."}
            )

        if empresa and empresa.tiene_envios:
            opciones_validas = [
                Pedido.TipoEntrega.ENVIO_LOCAL,
                Pedido.TipoEntrega.ENVIO_NACIONAL,
            ]
            if tipo_entrega not in opciones_validas:
                raise serializers.ValidationError(
                    {
                        "tipo_entrega": (
                            "Esta empresa tiene envios; debe seleccionar envio local "
                            "o envio nacional."
                        )
                    }
                )
            if not TarifaEntrega.objects.filter(
                empresa=empresa,
                tipo_entrega=tipo_entrega,
                activa=True,
            ).exists():
                raise serializers.ValidationError(
                    {
                        "envio": (
                            "No hay una tarifa activa configurada para este tipo de entrega."
                        )
                    }
                )

        if empresa and not empresa.tiene_envios:
            if tipo_entrega != Pedido.TipoEntrega.RETIRO_EN_LOCAL:
                raise serializers.ValidationError(
                    {
                        "tipo_entrega": (
                            "Esta empresa no tiene envios; solo permite retiro en local."
                        )
                    }
                )

        return attrs


class GenerarPedidoDesdeCarritoSerializer(serializers.Serializer):
    tipo_entrega = serializers.ChoiceField(choices=Pedido.TipoEntrega.choices)
    observaciones = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )


class TarifaEntregaSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    tipo_entrega_nombre = serializers.CharField(source="get_tipo_entrega_display", read_only=True)

    class Meta:
        model = TarifaEntrega
        fields = [
            "id",
            "empresa",
            "empresa_nombre",
            "tipo_entrega",
            "tipo_entrega_nombre",
            "monto",
            "activa",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id",
            "empresa_nombre",
            "tipo_entrega_nombre",
            "fecha_creacion",
            "fecha_actualizacion",
        ]

    def validate(self, attrs):
        request = self.context.get("request")
        empresa = attrs.get("empresa") or getattr(self.instance, "empresa", None)

        if request and not request.user.is_superuser:
            perfil = getattr(request.user, "perfil", None)
            if perfil and perfil.es_administrador_empresa:
                empresa_enviada = attrs.get("empresa")
                if empresa_enviada and empresa_enviada != perfil.empresa:
                    raise serializers.ValidationError(
                        {
                            "empresa": (
                                "El administrador de empresa solo puede cambiar "
                                "tarifas de su propia empresa."
                            )
                        }
                    )
                empresa = perfil.empresa

        if empresa and not empresa.tiene_envios:
            raise serializers.ValidationError(
                {
                    "empresa": (
                        "Esta empresa no tiene envios activos; no debe tener tarifas "
                        "de envio."
                    )
                }
            )

        return attrs


class PrefacturaDetalleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetallePedido
        fields = [
            "codigo_barra",
            "nombre_producto",
            "precio_unitario",
            "cantidad",
            "subtotal",
        ]
        read_only_fields = fields


class PrefacturaSerializer(serializers.ModelSerializer):
    numero_prefactura = serializers.CharField(source="numero", read_only=True)
    numero_pedido = serializers.CharField(source="pedido.numero", read_only=True)
    fecha_pedido = serializers.DateTimeField(source="pedido.fecha_creacion", read_only=True)
    fecha_prefactura = serializers.DateTimeField(source="fecha_creacion", read_only=True)
    empresa = serializers.SerializerMethodField()
    cliente = serializers.SerializerMethodField()
    tipo_entrega = serializers.CharField(source="pedido.tipo_entrega", read_only=True)
    tipo_entrega_nombre = serializers.CharField(
        source="pedido.get_tipo_entrega_display",
        read_only=True,
    )
    direccion_entrega = serializers.SerializerMethodField()
    metodo_pago = serializers.SerializerMethodField()
    estado_pago = serializers.CharField(source="pedido.estado_pago", read_only=True)
    estado_pago_nombre = serializers.CharField(
        source="pedido.get_estado_pago_display",
        read_only=True,
    )
    moneda = serializers.CharField(source="pedido.moneda", read_only=True)
    subtotal = serializers.DecimalField(
        source="pedido.subtotal",
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )
    descuento_total = serializers.DecimalField(
        source="pedido.descuento_total",
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )
    impuesto = serializers.DecimalField(
        source="pedido.impuesto",
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )
    envio = serializers.DecimalField(
        source="pedido.envio",
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )
    total = serializers.DecimalField(
        source="pedido.total",
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )
    detalles = PrefacturaDetalleSerializer(
        source="pedido.detalles",
        many=True,
        read_only=True,
    )

    class Meta:
        model = Prefactura
        fields = [
            "numero_prefactura",
            "numero_pedido",
            "fecha_pedido",
            "fecha_prefactura",
            "empresa",
            "cliente",
            "tipo_entrega",
            "tipo_entrega_nombre",
            "direccion_entrega",
            "detalles",
            "subtotal",
            "descuento_total",
            "impuesto",
            "envio",
            "total",
            "moneda",
            "metodo_pago",
            "estado_pago",
            "estado_pago_nombre",
            "leyenda",
        ]
        read_only_fields = fields

    def get_empresa(self, obj):
        empresa = obj.pedido.empresa
        return {
            "nombre": empresa.nombre,
            "telefono": empresa.telefono,
            "correo": empresa.correo,
            "direccion": empresa.direccion,
            "sitio_web": empresa.sitio_web,
        }

    def get_cliente(self, obj):
        usuario = obj.pedido.usuario
        perfil = getattr(usuario, "perfil", None)
        return {
            "nombre": usuario.get_full_name() or usuario.username,
            "correo": usuario.email,
            "telefono": perfil.telefono if perfil else "",
            "numero_identidad": perfil.numero_identidad if perfil else "",
        }

    def get_direccion_entrega(self, obj):
        return None

    def get_metodo_pago(self, obj):
        return "pendiente_integracion_pago"
