from rest_framework import decorators, response, status, views, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated

from .models import PerfilUsuario
from .permissions import IsSuperUserOrReadOwnProfile
from .serializers import (
    ConfirmarRecuperacionContrasenaSerializer,
    LoginJWTSerializer,
    PerfilUsuarioSerializer,
    ReenviarVerificacionCorreoSerializer,
    RegistroCompradorSerializer,
    SolicitarRecuperacionContrasenaSerializer,
    VerificarCorreoSerializer,
)


class LoginJWTView(views.APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginJWTSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        return response.Response(serializer.validated_data, status=status.HTTP_200_OK)


class RegistroCompradorView(views.APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegistroCompradorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return response.Response(serializer.data, status=status.HTTP_201_CREATED)


class VerificarCorreoView(views.APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerificarCorreoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return response.Response(serializer.data, status=status.HTTP_200_OK)


class ReenviarVerificacionCorreoView(views.APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ReenviarVerificacionCorreoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return response.Response(serializer.data, status=status.HTTP_200_OK)


class SolicitarRecuperacionContrasenaView(views.APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SolicitarRecuperacionContrasenaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return response.Response(serializer.data, status=status.HTTP_200_OK)


class ConfirmarRecuperacionContrasenaView(views.APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ConfirmarRecuperacionContrasenaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return response.Response(serializer.data, status=status.HTTP_200_OK)


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
