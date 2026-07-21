from django.db.models import Q

from rest_framework import viewsets
from rest_framework.permissions import SAFE_METHODS

from .models import Categoria, Familia, Producto
from .permissions import IsCatalogoManagerOrReadOnly
from .serializers import CategoriaSerializer, FamiliaSerializer, ProductoSerializer


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
            queryset = queryset.filter(existencia=0)
        elif queryset.model == Producto and agotado in ["false", "0", "no"]:
            queryset = queryset.filter(existencia__gt=0)

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
