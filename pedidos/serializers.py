from django.db.models import Prefetch, Q
from django.db.models.functions import Lower

from rest_framework import serializers

from catalogo.models import PaqueteCatalogo, PaqueteProducto, Producto
from empresas.models import Empresa

from .models import (
    Carrito,
    DetallePedido,
    DetallePedidoComponente,
    ItemCarrito,
    Pedido,
    Prefactura,
    TarifaEntrega,
)


TIPOS_ARTICULO_CARRITO = [
    ("producto", "Producto o servicio"),
    (PaqueteCatalogo.Tipo.PERFIL, "Perfil"),
    (PaqueteCatalogo.Tipo.COMBO, "Combo"),
]


class ItemCarritoSerializer(serializers.ModelSerializer):
    articulo_nombre = serializers.SerializerMethodField()
    codigo = serializers.SerializerMethodField()
    codigo_interno = serializers.SerializerMethodField()
    codigo_barra = serializers.SerializerMethodField()
    tipo_articulo = serializers.CharField(read_only=True)
    tipo_item = serializers.SerializerMethodField()
    controla_inventario = serializers.BooleanField(read_only=True)
    agotado = serializers.BooleanField(read_only=True)
    imagen_final = serializers.SerializerMethodField()
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = ItemCarrito
        fields = [
            "id",
            "carrito",
            "producto",
            "paquete",
            "articulo_nombre",
            "codigo",
            "codigo_interno",
            "codigo_barra",
            "tipo_articulo",
            "tipo_item",
            "controla_inventario",
            "agotado",
            "imagen_final",
            "cantidad",
            "precio_unitario",
            "subtotal",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id",
            "articulo_nombre",
            "codigo",
            "codigo_interno",
            "codigo_barra",
            "tipo_articulo",
            "tipo_item",
            "controla_inventario",
            "agotado",
            "imagen_final",
            "precio_unitario",
            "subtotal",
            "fecha_creacion",
            "fecha_actualizacion",
        ]

    def validate(self, attrs):
        carrito = attrs.get("carrito") or getattr(self.instance, "carrito", None)
        producto = attrs.get("producto")
        if "producto" not in attrs and self.instance:
            producto = self.instance.producto
        paquete = attrs.get("paquete")
        if "paquete" not in attrs and self.instance:
            paquete = self.instance.paquete
        cantidad = attrs.get("cantidad") or getattr(self.instance, "cantidad", 1)

        if bool(producto) == bool(paquete):
            raise serializers.ValidationError(
                "Debes seleccionar un producto, perfil o combo, pero no varios."
            )

        if carrito and not carrito.activo:
            raise serializers.ValidationError(
                {"carrito": "Este carrito ya no esta activo."}
            )

        if producto and not producto.activo:
            raise serializers.ValidationError(
                {"producto": "El producto ya no esta activo."}
            )

        if carrito and producto and carrito.empresa_id != producto.empresa_id:
            raise serializers.ValidationError(
                {"producto": "El producto debe pertenecer a la empresa del carrito."}
            )

        if (
            producto
            and producto.controla_inventario
            and cantidad > producto.existencia
        ):
            raise serializers.ValidationError(
                {"cantidad": "La cantidad no puede superar la existencia disponible."}
            )

        if carrito and paquete and carrito.empresa_id != paquete.empresa_id:
            raise serializers.ValidationError(
                {"paquete": "El perfil o combo debe pertenecer a la empresa del carrito."}
            )

        if paquete:
            if not paquete.activo:
                raise serializers.ValidationError(
                    {"paquete": "El perfil o combo ya no esta activo."}
                )

            for componente in paquete.items_productos.select_related("producto"):
                articulo = componente.producto
                if not articulo.activo:
                    raise serializers.ValidationError(
                        {
                            "paquete": (
                                f"El componente {articulo.nombre} ya no esta activo."
                            )
                        }
                    )
                if (
                    articulo.controla_inventario
                    and cantidad * componente.cantidad > articulo.existencia
                ):
                    raise serializers.ValidationError(
                        {
                            "cantidad": (
                                f"El paquete {paquete.nombre} no tiene existencia "
                                f"suficiente de {articulo.nombre}."
                            )
                        }
                    )

        return attrs

    def get_articulo_nombre(self, obj):
        return obj.nombre_articulo

    def get_codigo(self, obj):
        return obj.codigo_articulo

    def get_codigo_interno(self, obj):
        if obj.producto_id:
            return obj.producto.codigo_interno

        return obj.paquete.codigo

    def get_codigo_barra(self, obj):
        return obj.producto.codigo_barra if obj.producto_id else None

    def get_tipo_item(self, obj):
        return obj.producto.tipo_item if obj.producto_id else obj.paquete.tipo

    def get_imagen_final(self, obj):
        return self._imagen_absoluta(obj.articulo.imagen_final)

    def _imagen_absoluta(self, imagen):
        if not imagen:
            return None

        if imagen.startswith(("http://", "https://")):
            return imagen

        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(imagen)

        return imagen


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


class ItemCarritoClienteSerializer(ItemCarritoSerializer):
    class Meta(ItemCarritoSerializer.Meta):
        fields = [
            "id",
            "articulo_nombre",
            "codigo",
            "codigo_interno",
            "codigo_barra",
            "tipo_articulo",
            "tipo_item",
            "controla_inventario",
            "agotado",
            "imagen_final",
            "cantidad",
            "precio_unitario",
            "subtotal",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = fields


class CarritoClienteSerializer(serializers.ModelSerializer):
    items = ItemCarritoClienteSerializer(many=True, read_only=True)
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    empresa_slug = serializers.CharField(source="empresa.slug", read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Carrito
        fields = [
            "id",
            "empresa_nombre",
            "empresa_slug",
            "activo",
            "total_items",
            "subtotal",
            "items",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = fields


class DetallePedidoComponenteSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetallePedidoComponente
        fields = [
            "codigo_interno",
            "codigo_barra",
            "nombre_producto",
            "cantidad_por_unidad",
        ]
        read_only_fields = fields


class DetallePedidoSerializer(serializers.ModelSerializer):
    componentes = DetallePedidoComponenteSerializer(many=True, read_only=True)

    class Meta:
        model = DetallePedido
        fields = [
            "id",
            "pedido",
            "producto",
            "paquete",
            "tipo_articulo",
            "codigo_articulo",
            "nombre_articulo",
            "codigo_interno",
            "codigo_barra",
            "nombre_producto",
            "precio_unitario",
            "cantidad",
            "subtotal",
            "promocion_codigo",
            "promocion_titulo",
            "porcentaje_descuento",
            "descuento_unitario",
            "precio_unitario_final",
            "descuento_total",
            "subtotal_final",
            "componentes",
        ]
        read_only_fields = fields

class PedidoSerializer(serializers.ModelSerializer):
    detalles = DetallePedidoSerializer(many=True, read_only=True)
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    usuario_nombre = serializers.CharField(source="usuario.username", read_only=True)
    cancelado_por_email = serializers.EmailField(
        source="cancelado_por.email",
        read_only=True,
        allow_null=True,
    )

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
            "nombre_recibe",
            "telefono_recibe",
            "direccion_entrega",
            "referencia_entrega",
            "departamento_entrega",
            "municipio_entrega",
            "estado_pago",
            "metodo_pago",
            "sucursal_pago",
            "subtotal",
            "descuento_total",
            "impuesto",
            "aplica_impuesto",
            "tasa_impuesto",
            "envio",
            "total",
            "moneda",
            "observaciones",
            "inventario_descontado",
            "motivo_cancelacion",
            "cancelado_por",
            "cancelado_por_email",
            "fecha_cancelacion",
            "detalles",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = fields


class GenerarPedidoDesdeCarritoSerializer(serializers.Serializer):
    tipo_entrega = serializers.ChoiceField(choices=Pedido.TipoEntrega.choices)
    observaciones = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )
    nombre_recibe = serializers.CharField(required=False, allow_blank=True, default="")
    telefono_recibe = serializers.CharField(required=False, allow_blank=True, default="")
    direccion_entrega = serializers.CharField(required=False, allow_blank=True, default="")
    referencia_entrega = serializers.CharField(required=False, allow_blank=True, default="")
    departamento_entrega = serializers.CharField(required=False, allow_blank=True, default="")
    municipio_entrega = serializers.CharField(required=False, allow_blank=True, default="")


class PagoEnSucursalSerializer(serializers.Serializer):
    sucursal_id = serializers.IntegerField(min_value=1)


class CancelarPedidoPendienteSerializer(serializers.Serializer):
    motivo = serializers.CharField(max_length=1000, trim_whitespace=True)

    def validate_motivo(self, value):
        if not value:
            raise serializers.ValidationError("El motivo es obligatorio.")
        return value


class AgregarArticuloCarritoSerializer(serializers.Serializer):
    codigo = serializers.CharField(max_length=80)
    tipo_articulo = serializers.ChoiceField(
        choices=TIPOS_ARTICULO_CARRITO,
        required=False,
    )
    cantidad = serializers.IntegerField(min_value=1, default=1)

    def validate_codigo(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("El codigo no puede estar vacio.")
        return value


class LineaCalculoCarritoEntradaSerializer(serializers.Serializer):
    codigo = serializers.CharField(max_length=80)
    tipo_articulo = serializers.ChoiceField(
        choices=TIPOS_ARTICULO_CARRITO,
        required=False,
    )
    cantidad = serializers.IntegerField(min_value=1, max_value=999)

    def validate_codigo(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("El codigo no puede estar vacio.")
        return value


class CalcularCarritoEntradaSerializer(serializers.Serializer):
    empresa_slug = serializers.CharField(max_length=80)
    items = LineaCalculoCarritoEntradaSerializer(
        many=True,
        allow_empty=False,
        max_length=100,
    )

    def validate(self, attrs):
        empresa_slug = attrs["empresa_slug"].strip()
        empresa = Empresa.objects.filter(
            slug__iexact=empresa_slug,
            activa=True,
        ).first()
        if not empresa:
            raise serializers.ValidationError(
                {"empresa_slug": "La empresa no existe o no esta activa."}
            )

        items = attrs["items"]
        codigos_normalizados = [item["codigo"].casefold() for item in items]
        claves_normalizadas = [
            (
                item.get("tipo_articulo") or "",
                item["codigo"].casefold(),
            )
            for item in items
        ]
        if len(claves_normalizadas) != len(set(claves_normalizadas)):
            raise serializers.ValidationError(
                {"items": "Cada articulo debe aparecer una sola vez en el carrito."}
            )

        productos = (
            Producto.objects.filter(
                empresa=empresa,
                activo=True,
                familia__activa=True,
                categoria__activa=True,
            )
            .annotate(
                codigo_interno_normalizado=Lower("codigo_interno"),
                codigo_barra_normalizado=Lower("codigo_barra"),
            )
            .filter(
                Q(codigo_interno_normalizado__in=codigos_normalizados)
                | Q(codigo_barra_normalizado__in=codigos_normalizados)
            )
        )
        paquetes = (
            PaqueteCatalogo.objects.filter(
                empresa=empresa,
                activo=True,
            )
            .annotate(codigo_normalizado=Lower("codigo"))
            .filter(codigo_normalizado__in=codigos_normalizados)
            .prefetch_related(
                Prefetch(
                    "items_productos",
                    queryset=PaqueteProducto.objects.select_related(
                        "producto",
                        "producto__empresa",
                    ),
                )
            )
        )

        coincidencias = {codigo: [] for codigo in codigos_normalizados}
        for producto in productos:
            codigos_producto = {producto.codigo_interno.casefold()}
            if producto.codigo_barra:
                codigos_producto.add(producto.codigo_barra.casefold())
            for codigo in codigos_producto & coincidencias.keys():
                coincidencias[codigo].append(("producto", producto))

        for paquete in paquetes:
            coincidencias[paquete.codigo.casefold()].append(("paquete", paquete))

        coincidencias_filtradas = []
        for item, codigo in zip(items, codigos_normalizados):
            tipo_solicitado = item.get("tipo_articulo")
            candidatos = coincidencias[codigo]
            if tipo_solicitado == "producto":
                candidatos = [
                    candidato
                    for candidato in candidatos
                    if candidato[0] == "producto"
                ]
            elif tipo_solicitado in [
                PaqueteCatalogo.Tipo.PERFIL,
                PaqueteCatalogo.Tipo.COMBO,
            ]:
                candidatos = [
                    candidato
                    for candidato in candidatos
                    if candidato[0] == "paquete"
                    and candidato[1].tipo == tipo_solicitado
                ]
            coincidencias_filtradas.append(candidatos)

        no_encontrados = [
            item["codigo"]
            for item, candidatos in zip(items, coincidencias_filtradas)
            if not candidatos
        ]
        if no_encontrados:
            raise serializers.ValidationError(
                {
                    "items": (
                        "No existen o no estan activos estos articulos: "
                        + ", ".join(no_encontrados)
                    )
                }
            )

        ambiguos = [
            item["codigo"]
            for item, candidatos in zip(items, coincidencias_filtradas)
            if len(candidatos) > 1
        ]
        if ambiguos:
            raise serializers.ValidationError(
                {
                    "items": (
                        "Estos codigos coinciden con mas de un articulo: "
                        + ", ".join(ambiguos)
                    )
                }
            )

        lineas = []
        for item, candidatos in zip(items, coincidencias_filtradas):
            tipo, articulo = candidatos[0]
            if tipo == "producto":
                lineas.append(
                    {
                        "producto": articulo,
                        "paquete": None,
                        "cantidad": item["cantidad"],
                    }
                )
                continue

            for componente in articulo.items_productos.all():
                producto = componente.producto
                if not producto.activo:
                    raise serializers.ValidationError(
                        {
                            "items": (
                                f"El componente {producto.nombre} del paquete "
                                "ya no esta activo."
                            )
                        }
                    )
            lineas.append(
                {
                    "producto": None,
                    "paquete": articulo,
                    "cantidad": item["cantidad"],
                }
            )

        inventario_requerido = {}
        for linea in lineas:
            if linea["producto"]:
                componentes = [(linea["producto"], linea["cantidad"])]
            else:
                componentes = [
                    (
                        componente.producto,
                        linea["cantidad"] * componente.cantidad,
                    )
                    for componente in linea["paquete"].items_productos.all()
                ]

            for producto, cantidad in componentes:
                if not producto.controla_inventario:
                    continue
                inventario_requerido[producto.pk] = (
                    producto,
                    inventario_requerido.get(producto.pk, (producto, 0))[1]
                    + cantidad,
                )

        for producto, cantidad in inventario_requerido.values():
            if cantidad > producto.existencia:
                raise serializers.ValidationError(
                    {
                        "items": (
                            f"El articulo {producto.nombre} no tiene existencia "
                            "suficiente para completar el carrito."
                        )
                    }
                )

        attrs["empresa"] = empresa
        attrs["lineas"] = lineas
        return attrs


class DescuentoAplicadoCarritoSerializer(serializers.Serializer):
    codigo = serializers.CharField()
    titulo = serializers.CharField()
    alcance = serializers.CharField()
    porcentaje = serializers.IntegerField()


class LineaCalculoCarritoSalidaSerializer(serializers.Serializer):
    codigo = serializers.CharField()
    codigo_barra = serializers.CharField(allow_null=True)
    nombre = serializers.CharField()
    tipo_articulo = serializers.CharField()
    tipo_item = serializers.CharField()
    controla_inventario = serializers.BooleanField()
    cantidad = serializers.IntegerField()
    precio_unitario = serializers.DecimalField(max_digits=12, decimal_places=2)
    descuento_aplicado = DescuentoAplicadoCarritoSerializer(allow_null=True)
    descuento_unitario = serializers.DecimalField(max_digits=12, decimal_places=2)
    precio_unitario_final = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2)
    descuento_total = serializers.DecimalField(max_digits=12, decimal_places=2)
    subtotal_final = serializers.DecimalField(max_digits=12, decimal_places=2)


class CalcularCarritoSalidaSerializer(serializers.Serializer):
    empresa_slug = serializers.CharField()
    moneda = serializers.CharField()
    cobra_impuesto = serializers.BooleanField()
    porcentaje_impuesto = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
    )
    items = LineaCalculoCarritoSalidaSerializer(many=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2)
    descuento_total = serializers.DecimalField(max_digits=12, decimal_places=2)
    base_imponible = serializers.DecimalField(max_digits=12, decimal_places=2)
    impuesto = serializers.DecimalField(max_digits=12, decimal_places=2)
    envio = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_sin_envio = serializers.DecimalField(max_digits=12, decimal_places=2)


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
    componentes = DetallePedidoComponenteSerializer(many=True, read_only=True)

    class Meta:
        model = DetallePedido
        fields = [
            "tipo_articulo",
            "codigo_articulo",
            "nombre_articulo",
            "codigo_interno",
            "codigo_barra",
            "nombre_producto",
            "precio_unitario",
            "cantidad",
            "subtotal",
            "promocion_codigo",
            "promocion_titulo",
            "porcentaje_descuento",
            "descuento_unitario",
            "precio_unitario_final",
            "descuento_total",
            "subtotal_final",
            "componentes",
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
    sucursal = serializers.SerializerMethodField()
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
    aplica_impuesto = serializers.BooleanField(
        source="pedido.aplica_impuesto",
        read_only=True,
    )
    tasa_impuesto = serializers.DecimalField(
        source="pedido.tasa_impuesto",
        max_digits=5,
        decimal_places=4,
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
            "aplica_impuesto",
            "tasa_impuesto",
            "envio",
            "total",
            "moneda",
            "metodo_pago",
            "sucursal",
            "estado_pago",
            "estado_pago_nombre",
            "fecha_vencimiento",
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
        pedido = obj.pedido
        if pedido.tipo_entrega == Pedido.TipoEntrega.RETIRO_EN_LOCAL:
            return None

        return {
            "nombre_recibe": pedido.nombre_recibe,
            "telefono_recibe": pedido.telefono_recibe,
            "direccion": pedido.direccion_entrega,
            "referencia": pedido.referencia_entrega,
            "departamento": pedido.departamento_entrega,
            "municipio": pedido.municipio_entrega,
        }

    def get_metodo_pago(self, obj):
        return obj.pedido.metodo_pago

    def get_sucursal(self, obj):
        sucursal = obj.pedido.sucursal_pago
        if not sucursal:
            return None
        return {
            "id": sucursal.pk,
            "nombre": sucursal.nombre,
            "direccion": sucursal.direccion,
            "telefono": sucursal.telefono,
        }
