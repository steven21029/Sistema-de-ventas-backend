from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Favorito
from .permissions import IsFavoritoOwner
from .serializers import FavoritoSerializer


class FavoritoViewSet(
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = FavoritoSerializer
    permission_classes = [IsAuthenticated, IsFavoritoOwner]

    def get_queryset(self):
        queryset = Favorito.objects.select_related(
            "empresa",
            "usuario",
            "producto",
            "producto__familia",
            "producto__categoria",
            "paquete",
        ).prefetch_related("paquete__productos")
        empresa_slug = self.request.query_params.get("empresa_slug", "").strip()

        if self.request.user.is_superuser:
            if empresa_slug:
                return queryset.filter(empresa__slug__iexact=empresa_slug)

            return queryset

        perfil = getattr(self.request.user, "perfil", None)
        if not perfil or not perfil.activo or not perfil.empresa_id:
            return queryset.none()

        queryset = queryset.filter(usuario=self.request.user, empresa=perfil.empresa)
        if empresa_slug:
            queryset = queryset.filter(empresa__slug__iexact=empresa_slug)

        return queryset
