from django.db.models import Q
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from config.api import FiltroRangoFechasMixin, PaginacionAdministrativaOpcionalMixin
from empresas.contexto import empresas_administrables, obtener_empresa_administrable
from usuarios.models import PerfilUsuario
from .models import MensajeContacto
from .permissions import IsMensajeContactoAdmin
from .serializers import MensajeContactoAdminSerializer, MensajeContactoCreateSerializer


class MensajeContactoViewSet(
    PaginacionAdministrativaOpcionalMixin,
    FiltroRangoFechasMixin,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = MensajeContacto.objects.select_related("empresa")

    def get_permissions(self):
        if self.action == "create":
            return [AllowAny()]

        return [IsMensajeContactoAdmin()]

    def get_serializer_class(self):
        if self.action == "create":
            return MensajeContactoCreateSerializer

        return MensajeContactoAdminSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        empresa_slug = self.request.query_params.get("empresa_slug", "").strip()
        buscar = self.request.query_params.get("buscar", "").strip()

        if user.is_superuser:
            queryset = self._filtrar_empresa(queryset, empresa_slug)
        else:
            perfil = getattr(user, "perfil", None)
            if not perfil or not perfil.activo:
                return queryset.none()

            if perfil.es_administrador_maestro:
                queryset = queryset.filter(empresa__in=empresas_administrables(user))
                if empresa_slug:
                    obtener_empresa_administrable(self.request)
                    queryset = self._filtrar_empresa(queryset, empresa_slug)
            elif perfil.rol in [
                PerfilUsuario.Rol.ADMINISTRADOR_EMPRESA,
                PerfilUsuario.Rol.GERENTE,
            ] and perfil.empresa_id:
                obtener_empresa_administrable(self.request)
                queryset = queryset.filter(empresa=perfil.empresa)
            else:
                return queryset.none()

        if buscar:
            queryset = queryset.filter(
                Q(nombre__icontains=buscar)
                | Q(telefono__icontains=buscar)
                | Q(correo__icontains=buscar)
                | Q(asunto__icontains=buscar)
                | Q(mensaje__icontains=buscar)
            )

        estado = self.request.query_params.get("estado", "").strip()
        if estado:
            queryset = queryset.filter(estado=estado)

        queryset = self.filtrar_rango_fechas(queryset)
        orden = self.request.query_params.get("orden", "").strip()
        ordenes = {
            "fecha": ("fecha_creacion", "id"),
            "-fecha": ("-fecha_creacion", "-id"),
            "nombre": ("nombre", "id"),
            "-nombre": ("-nombre", "id"),
            "estado": ("estado", "-fecha_creacion"),
            "-estado": ("-estado", "-fecha_creacion"),
        }
        return queryset.order_by(*ordenes.get(orden, ("-fecha_creacion", "-id")))

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {
                "ok": True,
                "mensaje": "Mensaje recibido correctamente.",
            },
            status=status.HTTP_201_CREATED,
        )

    def _filtrar_empresa(self, queryset, empresa_slug):
        if empresa_slug:
            return queryset.filter(empresa__slug__iexact=empresa_slug)

        return queryset
