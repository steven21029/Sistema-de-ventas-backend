from django.conf import settings
from django.db.models import Q
from rest_framework import decorators, response, status, views, viewsets
from rest_framework import mixins
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from config.pagination import PaginacionAdministrativa
from empresas.contexto import empresas_administrables, obtener_empresa_administrable
from .models import PerfilUsuario
from .permissions import IsAdministrativeUser, IsSuperUserOrReadOwnProfile
from .services import revocar_sesiones_usuario
from .serializers import (
    ConfirmarRecuperacionContrasenaSerializer,
    LoginJWTSerializer,
    PerfilUsuarioSerializer,
    ReenviarVerificacionCorreoSerializer,
    RegistroCompradorSerializer,
    SesionLimitadaTokenRefreshSerializer,
    SolicitarRecuperacionContrasenaSerializer,
    UsuarioAdministrativoSerializer,
    VerificarCorreoSerializer,
)


def guardar_refresh_cookie(respuesta, refresh, max_age=None):
    respuesta.set_cookie(
        key=settings.JWT_REFRESH_COOKIE_NAME,
        value=refresh,
        max_age=(
            max_age if max_age is not None else settings.JWT_SESSION_MAX_SECONDS
        ),
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
        refresh_max_age = datos.pop("refresh_max_age")
        respuesta = response.Response(datos, status=status.HTTP_200_OK)
        guardar_refresh_cookie(respuesta, refresh, max_age=refresh_max_age)
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


class UsuarioAdministrativoViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = UsuarioAdministrativoSerializer
    permission_classes = [IsAuthenticated, IsAdministrativeUser]
    pagination_class = PaginacionAdministrativa

    def get_queryset(self):
        queryset = PerfilUsuario.objects.select_related(
            "usuario",
            "empresa",
        ).prefetch_related("empresas_permitidas")
        user = self.request.user
        empresa_slug = self.request.query_params.get("empresa_slug", "").strip()

        if user.is_superuser:
            if empresa_slug:
                queryset = queryset.filter(empresa__slug__iexact=empresa_slug)
        else:
            perfil = user.perfil
            if perfil.es_administrador_maestro:
                queryset = queryset.filter(
                    empresa__in=empresas_administrables(user),
                    rol__in=[
                        PerfilUsuario.Rol.ADMINISTRADOR_EMPRESA,
                        PerfilUsuario.Rol.GERENTE,
                        PerfilUsuario.Rol.COMPRADOR,
                    ],
                )
                if empresa_slug:
                    obtener_empresa_administrable(self.request)
                    queryset = queryset.filter(empresa__slug__iexact=empresa_slug)
            elif perfil.es_administrador_empresa:
                obtener_empresa_administrable(self.request)
                queryset = queryset.filter(
                    empresa=perfil.empresa,
                    rol__in=[PerfilUsuario.Rol.GERENTE, PerfilUsuario.Rol.COMPRADOR],
                )
            elif perfil.es_gerente:
                obtener_empresa_administrable(self.request)
                queryset = queryset.filter(
                    empresa=perfil.empresa,
                    rol=PerfilUsuario.Rol.COMPRADOR,
                )
            else:
                return queryset.none()

        buscar = self.request.query_params.get("buscar", "").strip()
        if buscar:
            queryset = queryset.filter(
                Q(usuario__username__icontains=buscar)
                | Q(usuario__email__icontains=buscar)
                | Q(usuario__first_name__icontains=buscar)
                | Q(usuario__last_name__icontains=buscar)
                | Q(telefono__icontains=buscar)
                | Q(numero_identidad__icontains=buscar)
            )

        rol = self.request.query_params.get("rol", "").strip()
        if rol:
            queryset = queryset.filter(rol=rol)
        activo = self.request.query_params.get("activo", "").strip().lower()
        if activo in ["true", "1", "si", "yes"]:
            queryset = queryset.filter(activo=True)
        elif activo in ["false", "0", "no"]:
            queryset = queryset.filter(activo=False)

        orden = self.request.query_params.get("orden", "").strip()
        ordenes = {
            "nombre": ("usuario__first_name", "usuario__last_name"),
            "-nombre": ("-usuario__first_name", "-usuario__last_name"),
            "email": ("usuario__email",),
            "-email": ("-usuario__email",),
            "fecha": ("fecha_creacion",),
            "-fecha": ("-fecha_creacion",),
        }
        return queryset.order_by(*ordenes.get(orden, ("usuario__username",)))

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.action in ["create", "update", "partial_update"]:
            if not self.request.user.is_superuser:
                context["empresa"] = obtener_empresa_administrable(self.request)
            elif self.request.query_params.get("empresa_slug"):
                context["empresa"] = obtener_empresa_administrable(self.request)
        return context

    def create(self, request, *args, **kwargs):
        if not self._puede_crear_usuarios():
            raise PermissionDenied("Tu perfil no puede crear usuarios.")
        return super().create(request, *args, **kwargs)

    def _puede_crear_usuarios(self):
        user = self.request.user
        if user.is_superuser:
            return True
        perfil = user.perfil
        return perfil.es_administrador_maestro or perfil.puede_crear_usuarios

    @decorators.action(detail=True, methods=["post"])
    def bloquear(self, request, pk=None):
        perfil = self.get_object()
        if perfil.usuario_id == request.user.id:
            raise ValidationError(
                {"usuario": "No puedes bloquear tu propia cuenta."}
            )
        if perfil.usuario.is_superuser:
            raise PermissionDenied("No puedes bloquear una cuenta superusuaria.")

        perfil.activo = False
        perfil.save(update_fields=["activo", "fecha_actualizacion"])
        perfil.usuario.is_active = False
        perfil.usuario.save(update_fields=["is_active"])
        revocar_sesiones_usuario(perfil.usuario)
        return response.Response(self.get_serializer(perfil).data)

    @decorators.action(detail=True, methods=["post"])
    def desbloquear(self, request, pk=None):
        perfil = self.get_object()
        if not perfil.correo_verificado:
            raise ValidationError(
                {"correo_verificado": "Verifica el correo antes de desbloquear."}
            )
        perfil.activo = True
        perfil.save(update_fields=["activo", "fecha_actualizacion"])
        perfil.usuario.is_active = True
        perfil.usuario.save(update_fields=["is_active"])
        return response.Response(self.get_serializer(perfil).data)
