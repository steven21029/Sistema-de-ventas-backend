from django.db.models import Q
from rest_framework import generics, response, views, viewsets
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny

from .models import Empresa, SucursalEmpresa
from .permissions import IsSuperUser
from .serializers import (
    EmpresaPublicaSerializer,
    EmpresaSerializer,
    SucursalEmpresaPublicaSerializer,
)


class EmpresaResolucionMixin:
    def resolver_empresa(self, request):
        host = self._obtener_host(request)
        slug = (
            request.query_params.get("empresa_slug", "").strip()
            or request.query_params.get("slug", "").strip()
        )

        empresa = Empresa.resolver_por_host(host)
        if not empresa and slug:
            empresa = Empresa.objects.filter(slug__iexact=slug, activa=True).first()

        if not empresa:
            raise NotFound("No se encontro una empresa activa para este dominio.")

        return empresa

    def _obtener_host(self, request):
        return (
            request.query_params.get("host", "").strip()
            or request.headers.get("X-Frontend-Host", "").strip()
            or request.get_host()
        )


class EmpresaActualView(EmpresaResolucionMixin, views.APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        empresa = self.resolver_empresa(request)
        serializer = EmpresaPublicaSerializer(empresa, context={"request": request})
        return response.Response(serializer.data)


class EmpresaMenuView(EmpresaResolucionMixin, views.APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        empresa = self.resolver_empresa(request)
        serializer = EmpresaPublicaSerializer(empresa, context={"request": request})
        return response.Response(serializer.data["menu"])


class SucursalEmpresaListView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = SucursalEmpresaPublicaSerializer

    def get_queryset(self):
        empresa_slug = self.request.query_params.get("empresa_slug", "").strip()
        if not empresa_slug:
            raise ValidationError({"empresa_slug": "Debes enviar el slug de la empresa."})

        queryset = SucursalEmpresa.objects.filter(
            empresa__slug__iexact=empresa_slug,
            empresa__activa=True,
            activa=True,
        )

        buscar = self.request.query_params.get("buscar", "").strip()
        if buscar:
            queryset = queryset.filter(
                Q(nombre__icontains=buscar)
                | Q(direccion__icontains=buscar)
                | Q(telefono__icontains=buscar)
                | Q(horario__icontains=buscar)
            )

        return queryset.order_by("orden", "nombre")


class EmpresaPublicaView(views.APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        slug = request.query_params.get("slug", "").strip()
        if not slug:
            raise ValidationError({"slug": "Debes enviar el slug de la empresa."})

        empresa = Empresa.objects.filter(slug__iexact=slug, activa=True).first()
        if not empresa:
            raise NotFound("La empresa no existe o no esta activa.")

        serializer = EmpresaPublicaSerializer(empresa, context={"request": request})
        return response.Response(serializer.data)


class EmpresaViewSet(viewsets.ModelViewSet):
    queryset = Empresa.objects.all()
    serializer_class = EmpresaSerializer
    permission_classes = [IsSuperUser]

    def perform_create(self, serializer):
        serializer.save(creada_por=self.request.user)
