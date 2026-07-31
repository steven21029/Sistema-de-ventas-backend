from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Prefetch, Q
from django.utils import timezone

from rest_framework import decorators, response, status, viewsets
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from catalogo.models import PaqueteCatalogo, Producto
from .models import Carrito, DetallePedido, ItemCarrito, Pedido, Prefactura, TarifaEntrega
from .permissions import IsPedidoOwnerOrEmpresaManager, IsTarifaEntregaAdmin
from .serializers import (
    AgregarArticuloCarritoSerializer,
    CalcularCarritoEntradaSerializer,
    CalcularCarritoSalidaSerializer,
    CarritoSerializer,
    CarritoClienteSerializer,
    DetallePedidoSerializer,
    GenerarPedidoDesdeCarritoSerializer,
    ItemCarritoSerializer,
    PedidoSerializer,
    PrefacturaSerializer,
    TarifaEntregaSerializer,
)
from .services import calcular_carrito


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
                [producto_item]
                if producto_item
                else list(paquete_item.productos.all())
            )
            for componente in componentes:
                if not componente.controla_inventario:
                    continue
                if componente.pk not in requeridos:
                    requeridos[componente.pk] = {
                        "producto": componente,
                        "cantidad": 0,
                    }
                requeridos[componente.pk]["cantidad"] += cantidad

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


class PedidoViewSet(EmpresaUsuarioMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = PedidoSerializer
    permission_classes = [IsPedidoOwnerOrEmpresaManager]

    def get_queryset(self):
        queryset = Pedido.objects.select_related(
            "empresa",
            "usuario",
            "carrito_origen",
        ).prefetch_related(
            "detalles__producto",
            "detalles__paquete",
            "detalles__componentes__producto",
        )

        if self.request.user.is_superuser:
            return queryset

        empresa = self.get_empresa_usuario()
        if self.request.user.perfil.es_gerente:
            return queryset.filter(empresa=empresa)

        return queryset.filter(empresa=empresa, usuario=self.request.user)

    @decorators.action(detail=True, methods=["get"], url_path="prefactura")
    def prefactura(self, request, pk=None):
        pedido = self.get_object()

        if pedido.estado_pago != Pedido.EstadoPago.PAGADO:
            raise ValidationError(
                {"pedido": "La prefactura solo esta disponible para pedidos pagados."}
            )

        prefactura = Prefactura.obtener_o_crear_para_pedido(pedido)
        serializer = PrefacturaSerializer(prefactura)
        return response.Response(serializer.data)


class DetallePedidoViewSet(viewsets.ReadOnlyModelViewSet):
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

        if self.request.user.is_superuser:
            return queryset

        perfil = getattr(self.request.user, "perfil", None)
        if not perfil or not perfil.empresa_id:
            return queryset.none()

        if perfil.es_gerente:
            return queryset.filter(pedido__empresa=perfil.empresa)

        return queryset.filter(pedido__empresa=perfil.empresa, pedido__usuario=self.request.user)


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
