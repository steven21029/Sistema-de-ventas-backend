from django.db.models import Count, IntegerField, Prefetch, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils.text import slugify

from rest_framework import generics, viewsets
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.permissions import SAFE_METHODS

from empresas.models import Empresa
from .models import Categoria, Familia, PaqueteCatalogo, Producto
from .permissions import IsCatalogoManagerOrReadOnly
from .serializers import (
    CategoriaSerializer,
    ComboDestacadoPublicoSerializer,
    FamiliaSerializer,
    PerfilPublicoSerializer,
    ProductoPaginaPublicaSerializer,
    ProductoSerializer,
    ServicioDetallePublicoSerializer,
    ServicioPublicoSerializer,
)


class EmpresaQuerysetMixin:
    def filtrar_por_empresa(self, queryset):
        user = self.request.user
        empresa_slug = self.request.query_params.get("empresa_slug", "").strip()

        if self.request.method in SAFE_METHODS and empresa_slug:
            queryset = queryset.filter(empresa__slug__iexact=empresa_slug, empresa__activa=True)
            queryset = self.filtrar_catalogo_publico(queryset)
            return self.aplicar_filtros_catalogo(queryset)

        if user.is_authenticated and user.is_superuser:
            return self.aplicar_filtros_catalogo(queryset)

        perfil = getattr(user, "perfil", None) if user.is_authenticated else None
        if perfil and perfil.empresa_id:
            return self.aplicar_filtros_catalogo(queryset.filter(empresa=perfil.empresa))

        return queryset.none()

    def filtrar_catalogo_publico(self, queryset):
        if queryset.model == Producto:
            return queryset.filter(
                activo=True,
                familia__activa=True,
                categoria__activa=True,
            )

        if queryset.model in [Familia, Categoria]:
            return queryset.filter(activa=True)

        return queryset

    def aplicar_filtros_catalogo(self, queryset):
        buscar = self.request.query_params.get("buscar", "").strip()
        familia = self.request.query_params.get("familia", "").strip()
        categoria = self.request.query_params.get("categoria", "").strip()
        agotado = self.request.query_params.get("agotado", "").strip().lower()
        orden = self.request.query_params.get("orden", "").strip().lower()

        if buscar:
            queryset = self._filtrar_busqueda(queryset, buscar)

        if familia:
            queryset = self._filtrar_familia(queryset, familia)

        if categoria:
            queryset = self._filtrar_categoria(queryset, categoria)

        if queryset.model == Producto and agotado in ["true", "1", "si", "yes"]:
            queryset = queryset.filter(
                tipo_item=Producto.TipoItem.PRODUCTO_FISICO,
                existencia=0,
            ).exclude(
                empresa__modo_inventario=Empresa.ModoInventario.SIN_INVENTARIO
            )
        elif queryset.model == Producto and agotado in ["false", "0", "no"]:
            queryset = queryset.filter(
                Q(tipo_item=Producto.TipoItem.SERVICIO)
                | Q(existencia__gt=0)
                | Q(
                    empresa__modo_inventario=Empresa.ModoInventario.SIN_INVENTARIO
                )
            )

        if queryset.model == Producto:
            if orden == "precio_asc":
                queryset = queryset.order_by("precio", "nombre")
            elif orden == "precio_desc":
                queryset = queryset.order_by("-precio", "nombre")
            elif orden == "nombre":
                queryset = queryset.order_by("nombre")

        return queryset

    def _filtrar_busqueda(self, queryset, buscar):
        if queryset.model == Producto:
            return queryset.filter(
                Q(nombre__icontains=buscar)
                | Q(codigo_interno__icontains=buscar)
                | Q(codigo_barra__icontains=buscar)
                | Q(descripcion__icontains=buscar)
                | Q(familia__nombre__icontains=buscar)
                | Q(categoria__nombre__icontains=buscar)
            )

        if queryset.model == Categoria:
            return queryset.filter(
                Q(nombre__icontains=buscar)
                | Q(descripcion__icontains=buscar)
                | Q(familia__nombre__icontains=buscar)
            )

        if queryset.model == Familia:
            return queryset.filter(
                Q(nombre__icontains=buscar) | Q(descripcion__icontains=buscar)
            )

        return queryset

    def _filtrar_familia(self, queryset, familia):
        if queryset.model == Producto:
            if familia.isdigit():
                return queryset.filter(familia_id=familia)

            return queryset.filter(familia__nombre__icontains=familia)

        if queryset.model == Categoria:
            if familia.isdigit():
                return queryset.filter(familia_id=familia)

            return queryset.filter(familia__nombre__icontains=familia)

        if queryset.model == Familia:
            if familia.isdigit():
                return queryset.filter(id=familia)

            return queryset.filter(nombre__icontains=familia)

        return queryset

    def _filtrar_categoria(self, queryset, categoria):
        if queryset.model == Producto:
            if categoria.isdigit():
                return queryset.filter(categoria_id=categoria)

            return queryset.filter(categoria__nombre__icontains=categoria)

        if queryset.model == Categoria:
            if categoria.isdigit():
                return queryset.filter(id=categoria)

            return queryset.filter(nombre__icontains=categoria)

        return queryset

    def asignar_empresa_si_corresponde(self, serializer):
        user = self.request.user

        if user.is_superuser:
            serializer.save()
            return

        serializer.save(empresa=user.perfil.empresa)


class FamiliaViewSet(EmpresaQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = FamiliaSerializer
    permission_classes = [IsCatalogoManagerOrReadOnly]

    def get_queryset(self):
        queryset = Familia.objects.select_related("empresa")
        return self.filtrar_por_empresa(queryset)

    def perform_create(self, serializer):
        self.asignar_empresa_si_corresponde(serializer)


class CategoriaViewSet(EmpresaQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = CategoriaSerializer
    permission_classes = [IsCatalogoManagerOrReadOnly]

    def get_queryset(self):
        queryset = Categoria.objects.select_related("empresa", "familia")
        return self.filtrar_por_empresa(queryset)

    def perform_create(self, serializer):
        self.asignar_empresa_si_corresponde(serializer)


class ProductoViewSet(EmpresaQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = ProductoSerializer
    permission_classes = [IsCatalogoManagerOrReadOnly]

    def get_queryset(self):
        queryset = Producto.objects.select_related("empresa", "familia", "categoria")
        return self.filtrar_por_empresa(queryset)

    def perform_create(self, serializer):
        self.asignar_empresa_si_corresponde(serializer)


class CatalogoPublicoEmpresaMixin:
    permission_classes = [AllowAny]

    def get_empresa_slug(self):
        empresa_slug = self.request.query_params.get("empresa_slug", "").strip()
        if not empresa_slug:
            raise ValidationError({"empresa_slug": "Debes enviar el slug de la empresa."})

        return empresa_slug

    def aplicar_busqueda(self, queryset):
        buscar = self.request.query_params.get("buscar", "").strip()
        if not buscar:
            return queryset

        return self.filtrar_busqueda(queryset, buscar)

    def filtrar_busqueda(self, queryset, buscar):
        return queryset


class ProductoPaginaPublicaMixin(CatalogoPublicoEmpresaMixin):
    serializer_class = ProductoPaginaPublicaSerializer

    def get_queryset(self):
        queryset = Producto.objects.select_related(
            "empresa",
            "familia",
            "categoria",
        ).filter(
            empresa__slug__iexact=self.get_empresa_slug(),
            empresa__activa=True,
            activo=True,
            familia__activa=True,
            categoria__activa=True,
        )
        queryset = self.aplicar_busqueda(queryset)
        return self.ordenar_productos(queryset)

    def filtrar_busqueda(self, queryset, buscar):
        return queryset.filter(
            Q(nombre__icontains=buscar)
            | Q(codigo_interno__icontains=buscar)
            | Q(codigo_barra__icontains=buscar)
            | Q(descripcion__icontains=buscar)
            | Q(familia__nombre__icontains=buscar)
            | Q(categoria__nombre__icontains=buscar)
        )

    def ordenar_productos(self, queryset):
        return queryset.order_by("nombre")


class ExamenesListView(ProductoPaginaPublicaMixin, generics.ListAPIView):
    pass


class ProductosMasVendidosListView(ProductoPaginaPublicaMixin, generics.ListAPIView):
    def ordenar_productos(self, queryset):
        queryset = queryset.annotate(
            total_vendido=Coalesce(
                Sum(
                    "detalles_pedido__cantidad",
                    filter=Q(
                        detalles_pedido__pedido__estado_pago="pagado",
                    ),
                ),
                Value(0),
                output_field=IntegerField(),
            )
        )
        return queryset.order_by("-total_vendido", "orden_destacado", "nombre")


class CombosDestacadosListView(CatalogoPublicoEmpresaMixin, generics.ListAPIView):
    serializer_class = ComboDestacadoPublicoSerializer

    def get_queryset(self):
        queryset = PaqueteCatalogo.objects.prefetch_related("productos").filter(
            empresa__slug__iexact=self.get_empresa_slug(),
            empresa__activa=True,
            tipo=PaqueteCatalogo.Tipo.COMBO,
            destacado=True,
            activo=True,
        )
        queryset = self.aplicar_busqueda(queryset)
        return queryset.order_by("orden", "nombre")

    def filtrar_busqueda(self, queryset, buscar):
        return queryset.filter(
            Q(nombre__icontains=buscar)
            | Q(codigo__icontains=buscar)
            | Q(descripcion__icontains=buscar)
            | Q(productos__nombre__icontains=buscar)
        ).distinct()


class PerfilesListView(CatalogoPublicoEmpresaMixin, generics.ListAPIView):
    serializer_class = PerfilPublicoSerializer

    def get_queryset(self):
        queryset = PaqueteCatalogo.objects.prefetch_related("productos").filter(
            empresa__slug__iexact=self.get_empresa_slug(),
            empresa__activa=True,
            tipo=PaqueteCatalogo.Tipo.PERFIL,
            activo=True,
        )
        queryset = self.aplicar_busqueda(queryset)
        return queryset.order_by("orden", "nombre")

    def filtrar_busqueda(self, queryset, buscar):
        return queryset.filter(
            Q(nombre__icontains=buscar)
            | Q(codigo__icontains=buscar)
            | Q(descripcion__icontains=buscar)
            | Q(productos__nombre__icontains=buscar)
        ).distinct()


class ServiciosListView(CatalogoPublicoEmpresaMixin, generics.ListAPIView):
    serializer_class = ServicioPublicoSerializer

    def get_queryset(self):
        categorias_activas = Categoria.objects.filter(activa=True).annotate(
            cantidad_productos=Count(
                "productos",
                filter=Q(productos__activo=True),
                distinct=True,
            )
        ).order_by("orden", "nombre")

        queryset = Familia.objects.filter(
            empresa__slug__iexact=self.get_empresa_slug(),
            empresa__activa=True,
            activa=True,
        ).annotate(
            cantidad_categorias=Count(
                "categorias",
                filter=Q(categorias__activa=True),
                distinct=True,
            ),
            cantidad_productos=Count(
                "productos",
                filter=Q(productos__activo=True),
                distinct=True,
            )
        ).prefetch_related(
            Prefetch(
                "categorias",
                queryset=categorias_activas,
                to_attr="categorias_activas",
            )
        )
        queryset = self.aplicar_busqueda(queryset)
        return queryset.order_by("orden", "nombre")

    def filtrar_busqueda(self, queryset, buscar):
        return queryset.filter(
            Q(nombre__icontains=buscar) | Q(descripcion__icontains=buscar)
        )


class ServicioDetallePublicoView(CatalogoPublicoEmpresaMixin, generics.RetrieveAPIView):
    serializer_class = ServicioDetallePublicoSerializer

    def get_object(self):
        empresa_slug = self.get_empresa_slug()
        servicio = (
            self.request.query_params.get("servicio", "").strip()
            or self.request.query_params.get("familia", "").strip()
            or self.request.query_params.get("clave", "").strip()
        )
        if not servicio:
            raise ValidationError(
                {
                    "servicio": (
                        "Debes enviar la clave o nombre del servicio, "
                        "por ejemplo servicio=imagenes."
                    )
                }
            )

        productos_activos = Producto.objects.filter(
            activo=True,
            familia__activa=True,
            categoria__activa=True,
        ).order_by("nombre")
        categorias_activas = Categoria.objects.filter(activa=True).annotate(
            cantidad_productos=Count(
                "productos",
                filter=Q(productos__activo=True),
                distinct=True,
            )
        ).prefetch_related(
            Prefetch(
                "productos",
                queryset=productos_activos,
                to_attr="productos_activos",
            )
        ).order_by("orden", "nombre")

        queryset = Familia.objects.filter(
            empresa__slug__iexact=empresa_slug,
            empresa__activa=True,
            activa=True,
        ).annotate(
            cantidad_categorias=Count(
                "categorias",
                filter=Q(categorias__activa=True),
                distinct=True,
            ),
            cantidad_productos=Count(
                "productos",
                filter=Q(productos__activo=True),
                distinct=True,
            )
        ).prefetch_related(
            Prefetch(
                "categorias",
                queryset=categorias_activas,
                to_attr="categorias_activas",
            )
        )

        servicio_normalizado = slugify(servicio).lower()
        for familia in queryset:
            if (
                slugify(familia.nombre).lower() == servicio_normalizado
                or familia.nombre.strip().lower() == servicio.strip().lower()
            ):
                return familia

        raise NotFound("Servicio no encontrado para esta empresa.")
