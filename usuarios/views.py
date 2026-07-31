from django.conf import settings
from rest_framework import decorators, response, status, views, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import PerfilUsuario
from .permissions import IsSuperUserOrReadOwnProfile
from .serializers import (
    ConfirmarRecuperacionContrasenaSerializer,
    LoginJWTSerializer,
    PerfilUsuarioSerializer,
    ReenviarVerificacionCorreoSerializer,
    RegistroCompradorSerializer,
    SesionLimitadaTokenRefreshSerializer,
    SolicitarRecuperacionContrasenaSerializer,
    VerificarCorreoSerializer,
)


def guardar_refresh_cookie(respuesta, refresh):
    respuesta.set_cookie(
        key=settings.JWT_REFRESH_COOKIE_NAME,
        value=refresh,
        max_age=settings.JWT_SESSION_MAX_SECONDS,
        path=settings.JWT_REFRESH_COOKIE_PATH,
        secure=settings.JWT_REFRESH_COOKIE_SECURE,
        httponly=True,
        samesite=settings.JWT_REFRESH_COOKIE_SAMESITE,
    )


def eliminar_refresh_cookie(respuesta):
    respuesta.set_cookie(
        key=settings.JWT_REFRESH_COOKIE_NAME,
        value="",
        max_age=0,
        path=settings.JWT_REFRESH_COOKIE_PATH,
        secure=settings.JWT_REFRESH_COOKIE_SECURE,
        httponly=True,
        samesite=settings.JWT_REFRESH_COOKIE_SAMESITE,
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
        datos = dict(serializer.validated_data)
        refresh = datos.pop("refresh")
        respuesta = response.Response(datos, status=status.HTTP_200_OK)
        guardar_refresh_cookie(respuesta, refresh)
        return respuesta


class RefreshJWTView(views.APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        refresh = request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME)
        if not refresh:
            return response.Response(
                {"detalle": "No hay una sesion disponible para renovar."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        serializer = SesionLimitadaTokenRefreshSerializer(
            data={"refresh": refresh}
        )
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError:
            return response.Response(
                {"detalle": "La sesion no es valida o ya vencio."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return response.Response(
            serializer.validated_data,
            status=status.HTTP_200_OK,
        )


class LogoutJWTView(views.APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        refresh = request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME)
        if refresh:
            try:
                RefreshToken(refresh).blacklist()
            except TokenError:
                pass

        respuesta = response.Response(
            {"detalle": "Sesion cerrada correctamente."},
            status=status.HTTP_200_OK,
        )
        eliminar_refresh_cookie(respuesta)
        return respuesta


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
