from rest_framework import mixins, viewsets

from .models import MovimientoInventario
from .permissions import IsInventarioManager
from .serializers import MovimientoInventarioSerializer


class MovimientoInventarioViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = MovimientoInventarioSerializer
    permission_classes = [IsInventarioManager]

    def get_queryset(self):
        queryset = MovimientoInventario.objects.select_related(
            "empresa",
            "producto",
            "usuario",
        )

        if self.request.user.is_superuser:
            return queryset

        perfil = getattr(self.request.user, "perfil", None)
        if perfil and perfil.empresa_id:
            return queryset.filter(empresa=perfil.empresa)

        return queryset.none()

    def perform_create(self, serializer):
        if self.request.user.is_superuser:
            serializer.save(usuario=self.request.user)
            return

        serializer.save(
            empresa=self.request.user.perfil.empresa,
            usuario=self.request.user,
        )
