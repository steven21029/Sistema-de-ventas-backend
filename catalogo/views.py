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
            return self.filtrar_catalogo_publico(queryset)

        if user.is_authenticated and user.is_superuser:
            return queryset

        perfil = getattr(user, "perfil", None) if user.is_authenticated else None
        if perfil and perfil.empresa_id:
            return queryset.filter(empresa=perfil.empresa)

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
