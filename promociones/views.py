from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import SAFE_METHODS

from config.api import EliminacionProtegidaMixin
from config.pagination import PaginacionAdministrativa
from empresas.contexto import empresas_administrables, obtener_empresa_administrable
from usuarios.models import PerfilUsuario
from .models import (
    BannerPromocional,
    DescuentoPromocional,
    OfertaPromocional,
)


class PromocionEmpresaMixin:
    pagination_class = PaginacionAdministrativa

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if (
            self.request.method not in SAFE_METHODS
            and self._usuario_admin_promociones()
            and not self.request.user.is_superuser
        ):
            context["empresa"] = obtener_empresa_administrable(self.request)
        return context

    def paginate_queryset(self, queryset):
        paginar = self.request.query_params.get("paginar", "").strip().lower()
        if self._usuario_admin_promociones() and paginar in ["true", "1", "si", "yes"]:
            return super().paginate_queryset(queryset)
        return None

    def _filtrar_por_empresa(self, queryset, empresa_slug):
        if self._usuario_admin_promociones():
            user = self.request.user
            if not user.is_superuser:
                if empresa_slug:
                    empresa = obtener_empresa_administrable(self.request)
                    return queryset.filter(empresa=empresa)
                queryset = queryset.filter(empresa__in=empresas_administrables(user))
            if empresa_slug:
                queryset = queryset.filter(empresa__slug__iexact=empresa_slug)
            return queryset

        if not empresa_slug:
            return queryset.none()
        return queryset.filter(empresa__slug__iexact=empresa_slug)

    def _guardar_en_empresa_autorizada(self, serializer):
        if self.request.user.is_superuser:
            serializer.save()
            return
        serializer.save(empresa=obtener_empresa_administrable(self.request))

    def _validar_slug_para_listado_publico(self):
        empresa_slug = self.request.query_params.get("empresa_slug", "").strip()
        if not self._usuario_admin_promociones() and not empresa_slug:
            raise ValidationError(
                {"empresa_slug": "Debes enviar el slug de la empresa."}
            )

    def _aplicar_orden(self, queryset, opciones, predeterminado):
        orden = self.request.query_params.get("orden", "").strip()
        return queryset.order_by(*opciones.get(orden, predeterminado))
from .permissions import IsBannerPromocionalAdminOrReadOnly
from .serializers import (
    BannerPromocionalPublicoSerializer,
    BannerPromocionalSerializer,
    DescuentoPromocionalPublicoSerializer,
    DescuentoPromocionalSerializer,
    OfertaPromocionalPublicaSerializer,
    OfertaPromocionalSerializer,
)


class BannerPromocionalViewSet(
    PromocionEmpresaMixin,
    EliminacionProtegidaMixin,
    viewsets.ModelViewSet,
):
    serializer_class = BannerPromocionalSerializer
    permission_classes = [IsBannerPromocionalAdminOrReadOnly]

    def get_serializer_class(self):
        if (
            self.request.method in SAFE_METHODS
            and not self._puede_ver_inactivos_como_admin()
        ):
            return BannerPromocionalPublicoSerializer

        return BannerPromocionalSerializer

    def get_queryset(self):
        queryset = BannerPromocional.objects.select_related("empresa")
        empresa_slug = self.request.query_params.get("empresa_slug", "").strip()

        if self.request.method in SAFE_METHODS:
            if not empresa_slug and not self.request.user.is_authenticated:
                return queryset.none()

            queryset = self._filtrar_por_empresa(queryset, empresa_slug)
            buscar = self.request.query_params.get("buscar", "").strip()
            if buscar:
                queryset = queryset.filter(
                    Q(titulo__icontains=buscar)
                    | Q(subtitulo__icontains=buscar)
                    | Q(texto_boton__icontains=buscar)
                )
            queryset = self._filtrar_publicos_si_corresponde(queryset)
            return self._aplicar_orden(
                queryset,
                {
                    "orden": ("orden", "-fecha_creacion"),
                    "-orden": ("-orden", "-fecha_creacion"),
                    "titulo": ("titulo",),
                    "-titulo": ("-titulo",),
                },
                ("orden", "-fecha_creacion"),
            )

        user = self.request.user
        if user.is_superuser:
            return self._filtrar_por_empresa(queryset, empresa_slug)

        perfil = getattr(user, "perfil", None)
        if not perfil or not perfil.activo:
            return queryset.none()

        if perfil.es_administrador_maestro:
            return self._filtrar_por_empresa(queryset, empresa_slug)

        if perfil.empresa_id and (
            perfil.es_administrador_empresa or perfil.es_gerente
        ):
            return queryset.filter(empresa=perfil.empresa)

        return queryset.none()

    def list(self, request, *args, **kwargs):
        self._validar_slug_para_listado_publico()
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        self._guardar_en_empresa_autorizada(serializer)

    def perform_update(self, serializer):
        self._guardar_en_empresa_autorizada(serializer)

    def _filtrar_publicos_si_corresponde(self, queryset):
        if self._puede_ver_inactivos_como_admin():
            return queryset

        ahora = timezone.now()
        return queryset.filter(
            empresa__activa=True,
            activo=True,
        ).filter(
            Q(fecha_inicio__isnull=True) | Q(fecha_inicio__lte=ahora),
            Q(fecha_fin__isnull=True) | Q(fecha_fin__gte=ahora),
        )

    def _puede_ver_inactivos_como_admin(self):
        return self._usuario_admin_promociones() and self._incluir_inactivos()

    def _incluir_inactivos(self):
        incluir_inactivos = (
            self.request.query_params.get("incluir_inactivos", "").strip().lower()
        )
        return incluir_inactivos in ["true", "1", "si", "yes"]

    def _usuario_admin_promociones(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        perfil = getattr(user, "perfil", None)
        return bool(
            perfil
            and perfil.activo
            and perfil.rol
            in [
                PerfilUsuario.Rol.ADMINISTRADOR_MAESTRO,
                PerfilUsuario.Rol.ADMINISTRADOR_EMPRESA,
                PerfilUsuario.Rol.GERENTE,
            ]
        )

# Create your views here.


class OfertaPromocionalViewSet(
    PromocionEmpresaMixin,
    EliminacionProtegidaMixin,
    viewsets.ModelViewSet,
):
    serializer_class = OfertaPromocionalSerializer
    permission_classes = [IsBannerPromocionalAdminOrReadOnly]

    def get_serializer_class(self):
        if (
            self.request.method in SAFE_METHODS
            and not self._puede_ver_inactivos_como_admin()
        ):
            return OfertaPromocionalPublicaSerializer

        return OfertaPromocionalSerializer

    def get_queryset(self):
        queryset = OfertaPromocional.objects.select_related(
            "empresa",
            "paquete",
        ).prefetch_related("items_productos__producto")
        empresa_slug = self.request.query_params.get("empresa_slug", "").strip()

        if self.request.method in SAFE_METHODS:
            if not empresa_slug and not self.request.user.is_authenticated:
                return queryset.none()

            queryset = self._filtrar_por_empresa(queryset, empresa_slug)
            queryset = self._filtrar_busqueda(queryset)
            return self._filtrar_publicas_si_corresponde(queryset)

        user = self.request.user
        if user.is_superuser:
            return self._filtrar_por_empresa(queryset, empresa_slug)

        perfil = getattr(user, "perfil", None)
        if not perfil or not perfil.activo:
            return queryset.none()

        if perfil.es_administrador_maestro:
            return self._filtrar_por_empresa(queryset, empresa_slug)

        if perfil.empresa_id and (
            perfil.es_administrador_empresa or perfil.es_gerente
        ):
            return queryset.filter(empresa=perfil.empresa)

        return queryset.none()

    def list(self, request, *args, **kwargs):
        self._validar_slug_para_listado_publico()
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        self._guardar_en_empresa_autorizada(serializer)

    def perform_update(self, serializer):
        self._guardar_en_empresa_autorizada(serializer)

    def _filtrar_busqueda(self, queryset):
        buscar = self.request.query_params.get("buscar", "").strip()
        if not buscar:
            return queryset

        return queryset.filter(
            Q(titulo__icontains=buscar)
            | Q(codigo__icontains=buscar)
            | Q(descripcion__icontains=buscar)
            | Q(productos__nombre__icontains=buscar)
            | Q(paquete__nombre__icontains=buscar)
            | Q(paquete__codigo__icontains=buscar)
        ).distinct()

    def _filtrar_publicas_si_corresponde(self, queryset):
        if self._puede_ver_inactivos_como_admin():
            return queryset

        ahora = timezone.now()
        return queryset.filter(
            empresa__activa=True,
            activo=True,
        ).filter(
            Q(fecha_inicio__isnull=True) | Q(fecha_inicio__lte=ahora),
            Q(fecha_fin__isnull=True) | Q(fecha_fin__gte=ahora),
        )

    def _puede_ver_inactivos_como_admin(self):
        return self._usuario_admin_promociones() and self._incluir_inactivos()

    def _incluir_inactivos(self):
        incluir_inactivos = (
            self.request.query_params.get("incluir_inactivos", "").strip().lower()
        )
        return incluir_inactivos in ["true", "1", "si", "yes"]

    def _usuario_admin_promociones(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        perfil = getattr(user, "perfil", None)
        return bool(
            perfil
            and perfil.activo
            and perfil.rol
            in [
                PerfilUsuario.Rol.ADMINISTRADOR_MAESTRO,
                PerfilUsuario.Rol.ADMINISTRADOR_EMPRESA,
                PerfilUsuario.Rol.GERENTE,
            ]
        )


class DescuentoPromocionalViewSet(
    PromocionEmpresaMixin,
    EliminacionProtegidaMixin,
    viewsets.ModelViewSet,
):
    serializer_class = DescuentoPromocionalSerializer
    permission_classes = [IsBannerPromocionalAdminOrReadOnly]

    def get_serializer_class(self):
        if (
            self.request.method in SAFE_METHODS
            and not self._puede_ver_inactivos_como_admin()
        ):
            return DescuentoPromocionalPublicoSerializer
        return DescuentoPromocionalSerializer

    def get_queryset(self):
        queryset = DescuentoPromocional.objects.select_related(
            "empresa"
        ).prefetch_related("productos")
        empresa_slug = self.request.query_params.get("empresa_slug", "").strip()

        if self.request.method in SAFE_METHODS:
            if not empresa_slug and not self.request.user.is_authenticated:
                return queryset.none()

            queryset = self._filtrar_por_empresa(queryset, empresa_slug)
            queryset = self._filtrar_busqueda(queryset)
            return self._filtrar_publicos_si_corresponde(queryset)

        user = self.request.user
        if user.is_superuser:
            return self._filtrar_por_empresa(queryset, empresa_slug)

        perfil = getattr(user, "perfil", None)
        if not perfil or not perfil.activo:
            return queryset.none()

        if perfil.es_administrador_maestro:
            return self._filtrar_por_empresa(queryset, empresa_slug)

        if perfil.empresa_id and (
            perfil.es_administrador_empresa or perfil.es_gerente
        ):
            return queryset.filter(empresa=perfil.empresa)

        return queryset.none()

    def list(self, request, *args, **kwargs):
        self._validar_slug_para_listado_publico()
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        self._guardar_en_empresa_autorizada(serializer)

    def perform_update(self, serializer):
        self._guardar_en_empresa_autorizada(serializer)

    def _filtrar_busqueda(self, queryset):
        buscar = self.request.query_params.get("buscar", "").strip()
        if not buscar:
            return queryset
        return queryset.filter(
            Q(titulo__icontains=buscar)
            | Q(codigo__icontains=buscar)
            | Q(descripcion__icontains=buscar)
            | Q(productos__nombre__icontains=buscar)
        ).distinct()

    def _filtrar_publicos_si_corresponde(self, queryset):
        if self._puede_ver_inactivos_como_admin():
            return queryset

        ahora = timezone.now()
        return queryset.filter(
            empresa__activa=True,
            activo=True,
        ).filter(
            Q(fecha_inicio__isnull=True) | Q(fecha_inicio__lte=ahora),
            Q(fecha_fin__isnull=True) | Q(fecha_fin__gte=ahora),
        )

    def _puede_ver_inactivos_como_admin(self):
        return self._usuario_admin_promociones() and self._incluir_inactivos()

    def _incluir_inactivos(self):
        incluir_inactivos = (
            self.request.query_params.get("incluir_inactivos", "").strip().lower()
        )
        return incluir_inactivos in ["true", "1", "si", "yes"]

    def _usuario_admin_promociones(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True

        perfil = getattr(user, "perfil", None)
        return bool(
            perfil
            and perfil.activo
            and perfil.rol
            in [
                PerfilUsuario.Rol.ADMINISTRADOR_MAESTRO,
                PerfilUsuario.Rol.ADMINISTRADOR_EMPRESA,
                PerfilUsuario.Rol.GERENTE,
            ]
        )
