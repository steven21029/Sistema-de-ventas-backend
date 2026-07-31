from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenVerifyView

from .views import (
    ConfirmarRecuperacionContrasenaView,
    LoginJWTView,
    LogoutJWTView,
    PerfilUsuarioViewSet,
    RefreshJWTView,
    ReenviarVerificacionCorreoView,
    RegistroCompradorView,
    SolicitarRecuperacionContrasenaView,
    VerificarCorreoView,
)

router = DefaultRouter()
router.register("usuarios/perfiles", PerfilUsuarioViewSet, basename="usuarios-perfiles")

urlpatterns = [
    path(
        "usuarios/registro-comprador/",
        RegistroCompradorView.as_view(),
        name="usuarios-registro-comprador",
    ),
    path(
        "usuarios/verificar-correo/",
        VerificarCorreoView.as_view(),
        name="usuarios-verificar-correo",
    ),
    path(
        "usuarios/reenviar-verificacion/",
        ReenviarVerificacionCorreoView.as_view(),
        name="usuarios-reenviar-verificacion",
    ),
    path(
        "usuarios/solicitar-recuperacion-contrasena/",
        SolicitarRecuperacionContrasenaView.as_view(),
        name="usuarios-solicitar-recuperacion-contrasena",
    ),
    path(
        "usuarios/confirmar-recuperacion-contrasena/",
        ConfirmarRecuperacionContrasenaView.as_view(),
        name="usuarios-confirmar-recuperacion-contrasena",
    ),
    path("usuarios/login/", LoginJWTView.as_view(), name="usuarios-login"),
    path(
        "usuarios/token/refresh/",
        RefreshJWTView.as_view(),
        name="usuarios-token-refresh",
    ),
    path(
        "usuarios/token/logout/",
        LogoutJWTView.as_view(),
        name="usuarios-token-logout",
    ),
    path(
        "usuarios/token/verify/",
        TokenVerifyView.as_view(),
        name="usuarios-token-verify",
    ),
    path("", include(router.urls)),
]
