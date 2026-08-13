from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Prefetch, Q
from django.http import HttpResponse
from django.utils import timezone

from rest_framework import decorators, response, status, viewsets
from rest_framework.exceptions import APIException, NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from catalogo.models import PaqueteCatalogo, Producto
from config.api import FiltroRangoFechasMixin, PaginacionAdministrativaOpcionalMixin
from empresas.contexto import empresas_administrables, obtener_empresa_administrable
from empresas.models import SucursalEmpresa
from pagos.models import Pago
from pagos.serializers import PagoSerializer
from usuarios.models import PerfilUsuario
from usuarios.permissions import IsAdministrativeUser
from .models import Carrito, DetallePedido, ItemCarrito, Pedido, Prefactura, TarifaEntrega
from .permissions import IsPedidoOwnerOrEmpresaManager, IsTarifaEntregaAdmin
from .serializers import (
    AgregarArticuloCarritoSerializer,
    CalcularCarritoEntradaSerializer,
    CalcularCarritoSalidaSerializer,
    CancelarPedidoPendienteSerializer,
    CarritoSerializer,
    CarritoClienteSerializer,
    DetallePedidoSerializer,
    GenerarPedidoDesdeCarritoSerializer,
    ItemCarritoSerializer,
    PagoEnSucursalSerializer,
    PedidoSerializer,
    PrefacturaSerializer,
    TarifaEntregaSerializer,
)
from .prefacturas import (
    ErrorEnvioCorreoPrefactura,
    LimiteIntentosCorreoPrefactura,
    PrefacturaVencida,
    correo_comprador_verificado,
    enmascarar_correo,
    enviar_prefactura_por_correo,
    generar_pdf_prefactura,
)
from .services import calcular_carrito
from .vencimientos import (
    MENSAJE_VIGENCIA_PREFACTURA,
    vencer_prefactura_sucursal,
    vencer_prefacturas_sucursal,
)


class CalcularCarritoPublicoView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        entrada = CalcularCarritoEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        empresa = entrada.validated_data["empresa"]
        calculo = calcular_carrito(
            empresa,
            entrada.validated_data["lineas"],
        )

        items = []
        for linea in calculo["lineas"]:
            producto = linea["producto"]
            paquete = linea["paquete"]
            descuento = linea["descuento"]
            items.append(
                {
                    "codigo": (
                        producto.codigo_venta if producto else paquete.codigo
                    ),
                    "codigo_barra": producto.codigo_barra if producto else None,
                    "nombre": producto.nombre if producto else paquete.nombre,
                    "tipo_articulo": "producto" if producto else paquete.tipo,
                    "tipo_item": producto.tipo_item if producto else paquete.tipo,
                    "controla_inventario": (
                        producto.controla_inventario if producto else False
                    ),
                    "cantidad": linea["cantidad"],
                    "precio_unitario": linea["precio_unitario"],
                    "descuento_aplicado": (
                        {
                            "codigo": descuento.codigo,
                            "titulo": descuento.titulo,
                            "alcance": descuento.alcance,
                            "porcentaje": descuento.porcentaje,
                        }
                        if descuento
                        else None
                    ),
                    "descuento_unitario": linea["descuento_unitario"],
                    "precio_unitario_final": linea["precio_unitario_final"],
                    "subtotal": linea["subtotal"],
                    "descuento_total": linea["descuento_total"],
                    "subtotal_final": linea["subtotal_final"],
                }
            )

        salida = CalcularCarritoSalidaSerializer(
            {
                "empresa_slug": empresa.slug,
                "moneda": "HNL",
                "cobra_impuesto": calculo["cobra_impuesto"],
                "porcentaje_impuesto": calculo["tasa_impuesto"] * Decimal("100"),
                "items": items,
                "subtotal": calculo["subtotal"],
                "descuento_total": calculo["descuento_total"],
                "base_imponible": calculo["base_imponible"],
                "impuesto": calculo["impuesto"],
                "envio": Decimal("0.00"),
                "total_sin_envio": calculo["total_sin_envio"],
            }
        )
        return response.Response(salida.data, status=status.HTTP_200_OK)


class EmpresaUsuarioMixin:
    def get_empresa_usuario(self):
        perfil = getattr(self.request.user, "perfil", None)
        if not perfil or not perfil.empresa_id:
            raise PermissionDenied("El usuario no tiene una empresa asignada.")

        return perfil.empresa


class CarritoViewSet(EmpresaUsuarioMixin, viewsets.ModelViewSet):
    serializer_class = CarritoSerializer
    permission_classes = [IsPedidoOwnerOrEmpresaManager]

    def get_queryset(self):
        items = ItemCarrito.objects.select_related(
            "producto",
            "producto__familia",
            "producto__categoria",
            "paquete",
        ).prefetch_related("paquete__productos")
        queryset = Carrito.objects.select_related(
            "empresa",
            "usuario",
        ).prefetch_related(
            Prefetch("items", queryset=items),
        )

        if self.request.user.is_superuser:
            return queryset

        empresa = self.get_empresa_usuario()
        if self.request.user.perfil.es_gerente:
            return queryset.filter(empresa=empresa)

        return queryset.filter(empresa=empresa, usuario=self.request.user)

    def perform_create(self, serializer):
        if self.request.user.is_superuser:
            serializer.save()
            return

        serializer.save(empresa=self.get_empresa_usuario(), usuario=self.request.user)

    @decorators.action(detail=False, methods=["get", "post"], url_path="mi-carrito")
    def mi_carrito(self, request):
        carrito, _created = Carrito.objects.get_or_create(
            empresa=self.get_empresa_usuario(),
            usuario=request.user,
            activo=True,
        )
        self._sincronizar_precios(carrito)
        serializer = CarritoClienteSerializer(
            carrito,
            context=self.get_serializer_context(),
        )
        return response.Response(serializer.data)

    @decorators.action(detail=True, methods=["post"], url_path="agregar-articulo")
    def agregar_articulo(self, request, pk=None):
        return self._agregar_articulo(request, pk)

    def _agregar_articulo(self, request, pk=None):
        carrito = self.get_object()
        if not carrito.activo:
            raise ValidationError({"carrito": "Este carrito ya no esta activo."})

        entrada_serializer = AgregarArticuloCarritoSerializer(data=request.data)
        entrada_serializer.is_valid(raise_exception=True)

        codigo = entrada_serializer.validated_data["codigo"]
        tipo_articulo = entrada_serializer.validated_data.get("tipo_articulo")
        producto = None
        paquete = None
        if tipo_articulo in [None, "producto"]:
            producto = (
                Producto.objects.filter(
                    Q(codigo_interno__iexact=codigo)
                    | Q(codigo_barra__iexact=codigo),
                    empresa=carrito.empresa,
                    activo=True,
                    familia__activa=True,
                    categoria__activa=True,
                )
                .select_related("empresa", "familia", "categoria")
                .first()
            )

        if tipo_articulo in [
            None,
            PaqueteCatalogo.Tipo.PERFIL,
            PaqueteCatalogo.Tipo.COMBO,
        ]:
            paquetes = PaqueteCatalogo.objects.filter(
                empresa=carrito.empresa,
                codigo__iexact=codigo,
                activo=True,
            )
            if tipo_articulo:
                paquetes = paquetes.filter(tipo=tipo_articulo)
            paquete = paquetes.prefetch_related(
                "items_productos__producto"
            ).first()

        if tipo_articulo is None and producto and paquete:
            raise ValidationError(
                {
                    "tipo_articulo": (
                        "El codigo coincide con mas de un tipo. "
                        "Debes indicar producto, perfil o combo."
                    )
                }
            )

        if not producto and not paquete:
            raise NotFound("El articulo no existe o no esta activo para esta empresa.")

        if paquete:
            componente_inactivo = paquete.productos.filter(activo=False).first()
            if componente_inactivo:
                raise ValidationError(
                    {
                        "paquete": (
                            f"El componente {componente_inactivo.nombre} "
                            "ya no esta activo."
                        )
                    }
                )

        cantidad = entrada_serializer.validated_data["cantidad"]
        item = ItemCarrito.objects.filter(
            carrito=carrito,
            producto=producto,
            paquete=paquete,
        ).first()
        cantidad_total = cantidad + (item.cantidad if item else 0)
        self._validar_inventario_total(
            carrito=carrito,
            item_actual=item,
            producto=producto,
            paquete=paquete,
            cantidad_total=cantidad_total,
        )

        if item:
            item.cantidad = cantidad_total
            item.precio_unitario = (
                producto.precio if producto else paquete.precio_paquete
            )
            item.save(
                update_fields=[
                    "cantidad",
                    "precio_unitario",
                    "fecha_actualizacion",
                ]
            )
        else:
            ItemCarrito.objects.create(
                carrito=carrito,
                producto=producto,
                paquete=paquete,
                cantidad=cantidad,
            )

        carrito.fecha_actualizacion = timezone.now()
        carrito.save(update_fields=["fecha_actualizacion"])
        carrito.refresh_from_db()
        salida_serializer = CarritoClienteSerializer(
            carrito,
            context=self.get_serializer_context(),
        )
        return response.Response(salida_serializer.data, status=status.HTTP_200_OK)

    def _validar_inventario_total(
        self,
        carrito,
        item_actual,
        producto,
        paquete,
        cantidad_total,
    ):
        items = list(
            ItemCarrito.objects.select_related(
                "producto",
                "paquete",
            )
            .prefetch_related("paquete__productos")
            .filter(carrito=carrito)
        )
        requeridos = {}

        def agregar_componentes(producto_item, paquete_item, cantidad):
            componentes = (
                [(producto_item, 1)]
                if producto_item
                else [
                    (item.producto, item.cantidad)
                    for item in paquete_item.items_productos.select_related("producto")
                ]
            )
            for componente, cantidad_por_paquete in componentes:
                if not componente.controla_inventario:
                    continue
                if componente.pk not in requeridos:
                    requeridos[componente.pk] = {
                        "producto": componente,
                        "cantidad": 0,
                    }
                requeridos[componente.pk]["cantidad"] += (
                    cantidad * cantidad_por_paquete
                )

        for item in items:
            if item_actual and item.pk == item_actual.pk:
                agregar_componentes(producto, paquete, cantidad_total)
            else:
                agregar_componentes(item.producto, item.paquete, item.cantidad)

        if not item_actual:
            agregar_componentes(producto, paquete, cantidad_total)

        for requerido in requeridos.values():
            articulo = requerido["producto"]
            if requerido["cantidad"] > articulo.existencia:
                raise ValidationError(
                    {
                        "cantidad": (
                            f"El articulo {articulo.nombre} no tiene existencia "
                            "suficiente para completar el carrito."
                        )
                    }
                )

    def _sincronizar_precios(self, carrito):
        items = list(
            carrito.items.select_related("producto", "paquete")
        )
        actualizados = []
        fecha = timezone.now()
        for item in items:
            precio_actual = (
                item.producto.precio
                if item.producto_id
                else item.paquete.precio_paquete
            )
            if item.precio_unitario == precio_actual:
                continue
            item.precio_unitario = precio_actual
            item.fecha_actualizacion = fecha
            actualizados.append(item)

        if actualizados:
            ItemCarrito.objects.bulk_update(
                actualizados,
                ["precio_unitario", "fecha_actualizacion"],
            )

    @decorators.action(detail=True, methods=["post"], url_path="generar-pedido")
    def generar_pedido(self, request, pk=None):
        carrito = self.get_object()
        entrada_serializer = GenerarPedidoDesdeCarritoSerializer(data=request.data)
        entrada_serializer.is_valid(raise_exception=True)

        try:
            pedido = Pedido.generar_desde_carrito(
                carrito=carrito,
                tipo_entrega=entrada_serializer.validated_data["tipo_entrega"],
                observaciones=entrada_serializer.validated_data.get("observaciones", ""),
                datos_entrega={
                    "nombre_recibe": entrada_serializer.validated_data.get(
                        "nombre_recibe",
                        "",
                    ),
                    "telefono_recibe": entrada_serializer.validated_data.get(
                        "telefono_recibe",
                        "",
                    ),
                    "direccion_entrega": entrada_serializer.validated_data.get(
                        "direccion_entrega",
                        "",
                    ),
                    "referencia_entrega": entrada_serializer.validated_data.get(
                        "referencia_entrega",
                        "",
                    ),
                    "departamento_entrega": entrada_serializer.validated_data.get(
                        "departamento_entrega",
                        "",
                    ),
                    "municipio_entrega": entrada_serializer.validated_data.get(
                        "municipio_entrega",
                        "",
                    ),
                    "municipio_entrega_catalogo": entrada_serializer.validated_data.get(
                        "municipio_entrega_catalogo",
                    ),
                },
            )
        except DjangoValidationError as exc:
            raise ValidationError(self._normalizar_error_django(exc)) from exc

        salida_serializer = PedidoSerializer(pedido, context=self.get_serializer_context())
        return response.Response(salida_serializer.data, status=status.HTTP_201_CREATED)

    def _normalizar_error_django(self, error):
        if hasattr(error, "message_dict"):
            return error.message_dict

        return {"detail": error.messages}


class ItemCarritoViewSet(viewsets.ModelViewSet):
    serializer_class = ItemCarritoSerializer
    permission_classes = [IsPedidoOwnerOrEmpresaManager]

    def perform_create(self, serializer):
        self._validar_carrito_destino(serializer.validated_data["carrito"])
        serializer.save()

    def perform_update(self, serializer):
        carrito = serializer.validated_data.get("carrito", serializer.instance.carrito)
        self._validar_carrito_destino(carrito)
        serializer.save()

    def _validar_carrito_destino(self, carrito):
        user = self.request.user
        if user.is_superuser:
            return

        perfil = getattr(user, "perfil", None)
        if not perfil or not perfil.activo or not perfil.empresa_id:
            raise PermissionDenied("Tu perfil no tiene una empresa activa.")

        if carrito.empresa_id != perfil.empresa_id:
            raise PermissionDenied("El carrito pertenece a otra empresa.")

        if not perfil.es_gerente and carrito.usuario_id != user.id:
            raise PermissionDenied("No puedes modificar el carrito de otro usuario.")

    def get_queryset(self):
        queryset = ItemCarrito.objects.select_related(
            "carrito",
            "carrito__empresa",
            "carrito__usuario",
            "producto",
            "producto__familia",
            "producto__categoria",
            "paquete",
        ).prefetch_related("paquete__productos")

        if self.request.user.is_superuser:
            return queryset

        perfil = getattr(self.request.user, "perfil", None)
        if not perfil or not perfil.empresa_id:
            return queryset.none()

        if perfil.es_gerente:
            return queryset.filter(carrito__empresa=perfil.empresa)

        return queryset.filter(carrito__empresa=perfil.empresa, carrito__usuario=self.request.user)


class PedidoViewSet(
    PaginacionAdministrativaOpcionalMixin,
    FiltroRangoFechasMixin,
    EmpresaUsuarioMixin,
    viewsets.ReadOnlyModelViewSet,
):
    serializer_class = PedidoSerializer
    permission_classes = [IsPedidoOwnerOrEmpresaManager]

    def get_permissions(self):
        if self.action == "cancelar_pendiente":
            return [IsAuthenticated(), IsAdministrativeUser()]
        return super().get_permissions()

    def get_queryset(self):
        self._actualizar_vencimientos_visibles()
        queryset = Pedido.objects.select_related(
            "empresa",
            "usuario",
            "usuario__perfil",
            "carrito_origen",
            "sucursal_pago",
            "cancelado_por",
            "prefactura",
        ).prefetch_related(
            "detalles__producto",
            "detalles__paquete",
            "detalles__componentes__producto",
        )

        user = self.request.user
        empresa_slug = self.request.query_params.get("empresa_slug", "").strip()
        if user.is_superuser:
            if empresa_slug:
                queryset = queryset.filter(empresa__slug__iexact=empresa_slug)
        else:
            perfil = getattr(user, "perfil", None)
            if not perfil or not perfil.activo:
                return queryset.none()
            if perfil.es_administrador_maestro:
                queryset = queryset.filter(empresa__in=empresas_administrables(user))
                if empresa_slug:
                    obtener_empresa_administrable(self.request)
                    queryset = queryset.filter(empresa__slug__iexact=empresa_slug)
            elif perfil.rol in [
                PerfilUsuario.Rol.ADMINISTRADOR_EMPRESA,
                PerfilUsuario.Rol.GERENTE,
            ] and perfil.empresa_id:
                obtener_empresa_administrable(self.request)
                queryset = queryset.filter(empresa=perfil.empresa)
            elif perfil.empresa_id:
                queryset = queryset.filter(empresa=perfil.empresa, usuario=user)
            else:
                return queryset.none()

        estado = (
            self.request.query_params.get("estado_pago", "").strip()
            or self.request.query_params.get("estado", "").strip()
        )
        if estado:
            queryset = queryset.filter(estado_pago=estado)

        cliente = self.request.query_params.get("cliente", "").strip()
        if cliente:
            queryset = queryset.filter(
                Q(usuario__username__icontains=cliente)
                | Q(usuario__email__icontains=cliente)
                | Q(usuario__first_name__icontains=cliente)
                | Q(usuario__last_name__icontains=cliente)
                | Q(nombre_recibe__icontains=cliente)
                | Q(telefono_recibe__icontains=cliente)
            )

        buscar = self.request.query_params.get("buscar", "").strip()
        if buscar:
            queryset = queryset.filter(
                Q(numero__icontains=buscar)
                | Q(nombre_recibe__icontains=buscar)
                | Q(telefono_recibe__icontains=buscar)
                | Q(usuario__email__icontains=buscar)
                | Q(observaciones__icontains=buscar)
            )

        queryset = self.filtrar_rango_fechas(queryset)
        orden = self.request.query_params.get("orden", "").strip()
        ordenes = {
            "fecha": ("fecha_creacion", "id"),
            "-fecha": ("-fecha_creacion", "-id"),
            "total": ("total", "id"),
            "-total": ("-total", "id"),
            "numero": ("numero",),
            "-numero": ("-numero",),
        }
        return queryset.order_by(*ordenes.get(orden, ("-fecha_creacion", "-id")))

    @decorators.action(
        detail=True,
        methods=["post"],
        url_path="cancelar-pendiente",
    )
    def cancelar_pendiente(self, request, pk=None):
        entrada = CancelarPedidoPendienteSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        pedido_consultado = Pedido.objects.select_related("empresa").filter(pk=pk).first()
        if not pedido_consultado:
            raise NotFound("No existe el pedido solicitado.")
        if not request.user.is_superuser and not empresas_administrables(
            request.user
        ).filter(pk=pedido_consultado.empresa_id).exists():
            raise PermissionDenied("No puedes cancelar pedidos de otra empresa.")

        try:
            with transaction.atomic():
                pagos = list(
                    Pago.objects.select_for_update()
                    .filter(pedido_id=pedido_consultado.pk)
                    .order_by("id")
                )
                pedido = (
                    Pedido.objects.select_for_update()
                    .select_related(
                        "empresa",
                        "usuario",
                        "cancelado_por",
                        "sucursal_pago",
                    )
                    .prefetch_related(
                        "detalles__producto",
                        "detalles__paquete",
                        "detalles__componentes__producto",
                    )
                    .get(pk=pedido_consultado.pk)
                )
                if any(pago.estado == Pago.Estado.APROBADO for pago in pagos):
                    raise DjangoValidationError(
                        {"pago": "El pedido tiene un pago aprobado."}
                    )
                es_reintento = bool(
                    pedido.estado_pago == Pedido.EstadoPago.CANCELADO
                    and pedido.fecha_cancelacion
                    and pedido.cancelado_por_id
                )
                if es_reintento:
                    pagos_cancelados = [
                        pago for pago in pagos if pago.estado == Pago.Estado.CANCELADO
                    ]
                else:
                    if pedido.estado_pago != Pedido.EstadoPago.PENDIENTE:
                        raise DjangoValidationError(
                            {
                                "estado_pago": (
                                    "Solo se puede cancelar un pedido pendiente."
                                )
                            }
                        )
                    pagos_cancelados = []
                    for pago in pagos:
                        if pago.estado != Pago.Estado.PENDIENTE:
                            continue
                        pago.cancelar_pendiente_administrativamente()
                        pagos_cancelados.append(pago)
                    pedido.cancelar_pendiente_administrativamente(
                        administrador=request.user,
                        motivo=entrada.validated_data["motivo"],
                    )
        except DjangoValidationError as exc:
            raise ValidationError(self._normalizar_error(exc)) from exc

        return response.Response(
            {
                "pedido": PedidoSerializer(
                    pedido,
                    context=self.get_serializer_context(),
                ).data,
                "pagos_cancelados": PagoSerializer(
                    pagos_cancelados,
                    many=True,
                ).data,
                "duplicado": es_reintento,
            },
            status=status.HTTP_200_OK,
        )

    @decorators.action(detail=True, methods=["get"], url_path="prefactura")
    def prefactura(self, request, pk=None):
        pedido = self.get_object()
        vencer_prefactura_sucursal(pedido.pk)
        pedido.refresh_from_db()
        prefactura = Prefactura.objects.filter(pedido=pedido).first()
        if not prefactura and not Prefactura.puede_generarse_para(pedido):
            raise ValidationError(
                {"pedido": "La prefactura no esta disponible para este pedido."}
            )
        if not prefactura:
            prefactura = Prefactura.obtener_o_crear_para_pedido(pedido)
        serializer = PrefacturaSerializer(prefactura)
        return response.Response(serializer.data)

    @decorators.action(
        detail=True,
        methods=["post"],
        url_path="pago-en-sucursal",
    )
    def pago_en_sucursal(self, request, pk=None):
        pedido = self.get_object()
        self._validar_comprador_propietario(pedido)
        entrada = PagoEnSucursalSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        sucursal = SucursalEmpresa.objects.filter(
            pk=entrada.validated_data["sucursal_id"],
            empresa=pedido.empresa,
            activa=True,
        ).first()
        if not sucursal:
            raise ValidationError(
                {"sucursal_id": "La sucursal no existe, esta inactiva o pertenece a otra empresa."}
            )
        try:
            correo = correo_comprador_verificado(pedido)
        except DjangoValidationError as exc:
            raise ValidationError(self._normalizar_error(exc)) from exc

        try:
            with transaction.atomic():
                sucursal = SucursalEmpresa.objects.select_for_update().filter(
                    pk=sucursal.pk,
                    empresa=pedido.empresa,
                    activa=True,
                ).first()
                if not sucursal:
                    raise DjangoValidationError(
                        {
                            "sucursal_id": (
                                "La sucursal dejo de estar disponible para este pago."
                            )
                        }
                    )
                pedido = (
                    Pedido.objects.select_for_update()
                    .select_related("empresa", "usuario")
                    .prefetch_related("detalles")
                    .get(pk=pedido.pk)
                )
                metodo_creado = pedido.seleccionar_metodo_pago(
                    Pedido.MetodoPago.SUCURSAL,
                    sucursal=sucursal,
                )
                pago, pago_creado = Pago.obtener_o_crear_pendiente(
                    pedido=pedido,
                    proveedor="sucursal",
                    metodo=Pago.Metodo.SUCURSAL,
                )
                prefactura_existia = Prefactura.objects.filter(pedido=pedido).exists()
                prefactura = Prefactura.obtener_o_crear_para_pedido(pedido)
        except DjangoValidationError as exc:
            raise ValidationError(self._normalizar_error(exc)) from exc

        if not prefactura.intentos_correo:
            try:
                enviar_prefactura_por_correo(prefactura)
            except PrefacturaVencida as exc:
                raise ValidationError({"prefactura": str(exc)}) from exc
            except ErrorEnvioCorreoPrefactura as exc:
                error = APIException(str(exc))
                error.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
                raise error from exc

        prefactura.refresh_from_db()
        pedido.refresh_from_db()
        codigo_estado = (
            status.HTTP_201_CREATED
            if metodo_creado or pago_creado or not prefactura_existia
            else status.HTTP_200_OK
        )
        return response.Response(
            {
                "pedido": {
                    "id": pedido.pk,
                    "numero": pedido.numero,
                    "estado_pago": pedido.estado_pago,
                    "metodo_pago": pedido.metodo_pago,
                },
                "pago": {
                    "referencia": str(pago.referencia),
                    "estado": pago.estado,
                    "metodo": pago.metodo,
                },
                "prefactura": {
                    "numero": prefactura.numero,
                    "url_pdf": (
                        request.path.removesuffix("pago-en-sucursal/")
                        + "prefactura/pdf/"
                    ),
                    "correo_enviado": bool(prefactura.correo_enviado_en),
                    "correo_destino": enmascarar_correo(correo),
                    "fecha_vencimiento": prefactura.fecha_vencimiento,
                    "vigencia_horas": settings.PREFACTURA_VIGENCIA_HORAS,
                    "vigente": prefactura.vigente_para_pago(),
                    "mensaje_vigencia": MENSAJE_VIGENCIA_PREFACTURA,
                },
            },
            status=codigo_estado,
        )

    @decorators.action(
        detail=True,
        methods=["get"],
        url_path="prefactura/pdf",
    )
    def prefactura_pdf(self, request, pk=None):
        pedido = self.get_object()
        vencer_prefactura_sucursal(pedido.pk)
        pedido.refresh_from_db()
        try:
            prefactura = Prefactura.objects.select_related(
                "pedido__empresa",
                "pedido__usuario__perfil",
                "pedido__sucursal_pago",
            ).prefetch_related("pedido__detalles").get(pedido=pedido)
        except Prefactura.DoesNotExist as exc:
            raise NotFound("El pedido no tiene una prefactura disponible.") from exc

        contenido = generar_pdf_prefactura(prefactura)
        respuesta = HttpResponse(contenido, content_type="application/pdf")
        respuesta["Content-Disposition"] = (
            f'attachment; filename="prefactura-{pedido.numero}.pdf"'
        )
        return respuesta

    @decorators.action(
        detail=True,
        methods=["post"],
        url_path="prefactura/reenviar-correo",
    )
    def reenviar_correo_prefactura(self, request, pk=None):
        pedido = self.get_object()
        self._validar_comprador_propietario(pedido)
        try:
            vencimiento = vencer_prefactura_sucursal(pedido.pk)
            if vencimiento.vencida:
                raise PrefacturaVencida(
                    "La prefactura vencio y el pedido fue rechazado. "
                    "Debe realizar una nueva compra."
                )
            prefactura = Prefactura.objects.select_related(
                "pedido__usuario__perfil",
                "pedido__empresa",
                "pedido__sucursal_pago",
            ).prefetch_related("pedido__detalles").get(pedido=pedido)
            correo = correo_comprador_verificado(pedido)
            enviar_prefactura_por_correo(prefactura, es_reenvio=True)
        except Prefactura.DoesNotExist as exc:
            raise NotFound("El pedido no tiene una prefactura disponible.") from exc
        except LimiteIntentosCorreoPrefactura as exc:
            error = APIException(str(exc))
            error.status_code = status.HTTP_429_TOO_MANY_REQUESTS
            raise error from exc
        except PrefacturaVencida as exc:
            raise ValidationError({"prefactura": str(exc)}) from exc
        except ErrorEnvioCorreoPrefactura as exc:
            error = APIException(str(exc))
            error.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            raise error from exc
        except DjangoValidationError as exc:
            raise ValidationError(self._normalizar_error(exc)) from exc

        prefactura.refresh_from_db()
        return response.Response(
            {
                "correo_enviado": True,
                "correo_destino": enmascarar_correo(correo),
                "intentos_restantes": max(
                    settings.PREFACTURA_MAX_INTENTOS_CORREO
                    - prefactura.intentos_correo,
                    0,
                ),
            }
        )

    def _validar_comprador_propietario(self, pedido):
        perfil = getattr(self.request.user, "perfil", None)
        if (
            pedido.usuario_id != self.request.user.id
            or not perfil
            or not perfil.activo
            or not perfil.es_comprador
        ):
            raise PermissionDenied(
                "Solo el comprador propietario puede gestionar este pago."
            )

    def _actualizar_vencimientos_visibles(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return
        if user.is_superuser:
            vencer_prefacturas_sucursal()
            return

        perfil = getattr(user, "perfil", None)
        if not perfil or not perfil.activo:
            return
        if perfil.es_administrador_maestro:
            empresa_ids = empresas_administrables(user).values_list("id", flat=True)
            vencer_prefacturas_sucursal(empresa_ids=empresa_ids)
            return
        if (
            perfil.rol
            in [
                PerfilUsuario.Rol.ADMINISTRADOR_EMPRESA,
                PerfilUsuario.Rol.GERENTE,
            ]
            and perfil.empresa_id
        ):
            vencer_prefacturas_sucursal(empresa_ids=[perfil.empresa_id])
            return
        vencer_prefacturas_sucursal(usuario_id=user.pk)

    def _normalizar_error(self, error):
        if hasattr(error, "message_dict"):
            return error.message_dict
        return {"detail": error.messages}


class DetallePedidoViewSet(
    PaginacionAdministrativaOpcionalMixin,
    FiltroRangoFechasMixin,
    viewsets.ReadOnlyModelViewSet,
):
    serializer_class = DetallePedidoSerializer
    permission_classes = [IsPedidoOwnerOrEmpresaManager]

    def get_queryset(self):
        queryset = DetallePedido.objects.select_related(
            "pedido",
            "pedido__empresa",
            "pedido__usuario",
            "producto",
            "paquete",
        ).prefetch_related("componentes__producto")

        user = self.request.user
        empresa_slug = self.request.query_params.get("empresa_slug", "").strip()
        if user.is_superuser:
            if empresa_slug:
                queryset = queryset.filter(pedido__empresa__slug__iexact=empresa_slug)
        else:
            perfil = getattr(user, "perfil", None)
            if not perfil or not perfil.activo:
                return queryset.none()
            if perfil.es_administrador_maestro:
                queryset = queryset.filter(
                    pedido__empresa__in=empresas_administrables(user)
                )
                if empresa_slug:
                    obtener_empresa_administrable(self.request)
                    queryset = queryset.filter(
                        pedido__empresa__slug__iexact=empresa_slug
                    )
            elif perfil.rol in [
                PerfilUsuario.Rol.ADMINISTRADOR_EMPRESA,
                PerfilUsuario.Rol.GERENTE,
            ] and perfil.empresa_id:
                obtener_empresa_administrable(self.request)
                queryset = queryset.filter(pedido__empresa=perfil.empresa)
            elif perfil.empresa_id:
                queryset = queryset.filter(
                    pedido__empresa=perfil.empresa,
                    pedido__usuario=user,
                )
            else:
                return queryset.none()

        pedido_numero = self.request.query_params.get("pedido", "").strip()
        if pedido_numero:
            queryset = queryset.filter(pedido__numero__icontains=pedido_numero)
        buscar = self.request.query_params.get("buscar", "").strip()
        if buscar:
            queryset = queryset.filter(
                Q(nombre_articulo__icontains=buscar)
                | Q(codigo_articulo__icontains=buscar)
                | Q(codigo_interno__icontains=buscar)
                | Q(codigo_barra__icontains=buscar)
            )
        queryset = self.filtrar_rango_fechas(queryset, campo="pedido__fecha_creacion")
        return queryset.order_by("-pedido__fecha_creacion", "id")


class TarifaEntregaViewSet(viewsets.ModelViewSet):
    serializer_class = TarifaEntregaSerializer
    permission_classes = [IsTarifaEntregaAdmin]

    def get_queryset(self):
        queryset = TarifaEntrega.objects.select_related("empresa")

        if self.request.user.is_superuser:
            return queryset

        perfil = getattr(self.request.user, "perfil", None)
        if not perfil or not perfil.activo:
            return queryset.none()

        if perfil.es_administrador_maestro:
            return queryset

        if perfil.es_administrador_empresa and perfil.empresa_id:
            return queryset.filter(empresa=perfil.empresa)

        return queryset.none()

    def perform_create(self, serializer):
        if self.request.user.is_superuser:
            serializer.save()
            return

        perfil = self.request.user.perfil
        if perfil.es_administrador_maestro:
            serializer.save()
            return

        serializer.save(empresa=perfil.empresa)

    def perform_update(self, serializer):
        if self.request.user.is_superuser:
            serializer.save()
            return

        perfil = self.request.user.perfil
        if perfil.es_administrador_maestro:
            serializer.save()
            return

        serializer.save(empresa=perfil.empresa)
