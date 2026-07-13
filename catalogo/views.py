from rest_framework import viewsets

from .models import Categoria, Familia, Producto
from .permissions import IsCatalogoManagerOrReadOnly
from .serializers import CategoriaSerializer, FamiliaSerializer, ProductoSerializer


class EmpresaQuerysetMixin:
    def filtrar_por_empresa(self, queryset):
        user = self.request.user

        if user.is_superuser:
            return queryset

        perfil = getattr(user, "perfil", None)
        if perfil and perfil.empresa_id:
            return queryset.filter(empresa=perfil.empresa)

        return queryset.none()

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
