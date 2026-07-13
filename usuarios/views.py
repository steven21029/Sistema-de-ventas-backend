from rest_framework import decorators, response, viewsets
from rest_framework.permissions import IsAuthenticated

from .models import PerfilUsuario
from .permissions import IsSuperUserOrReadOwnProfile
from .serializers import PerfilUsuarioSerializer


class PerfilUsuarioViewSet(viewsets.ModelViewSet):
    serializer_class = PerfilUsuarioSerializer
    permission_classes = [IsAuthenticated, IsSuperUserOrReadOwnProfile]

    def get_queryset(self):
        queryset = PerfilUsuario.objects.select_related("usuario", "empresa")

        if self.request.user.is_superuser:
            return queryset

        return queryset.filter(usuario=self.request.user)

    @decorators.action(detail=False, methods=["get"], url_path="mi-perfil")
    def mi_perfil(self, request):
        perfil, _created = PerfilUsuario.objects.get_or_create(
            usuario=request.user,
            defaults={
                "rol": (
                    PerfilUsuario.Rol.ADMINISTRADOR_MAESTRO
                    if request.user.is_superuser
                    else PerfilUsuario.Rol.COMPRADOR
                )
            },
        )
        serializer = self.get_serializer(perfil)
        return response.Response(serializer.data)
