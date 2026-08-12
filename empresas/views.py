from django.db.models import Q
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework import mixins, response, views, viewsets
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated

from usuarios.permissions import IsAdministrativeUser
from usuarios.serializers import PerfilUsuarioSerializer

from config.pagination import PaginacionAdministrativa
from .contexto import empresas_administrables, obtener_empresa_administrable
from .models import (
    Departamento,
    Empresa,
    ItemMenuEmpresa,
    Municipio,
    SobreNosotrosEmpresa,
    SucursalEmpresa,
)
from .permissions import IsSuperUser
from .serializers import (
    DepartamentoSerializer,
    EmpresaPublicaSerializer,
    EmpresaSerializer,
    EmpresaMiEmpresaSerializer,
    ItemMenuEmpresaAdminSerializer,
    MunicipioSerializer,
    SobreNosotrosEmpresaPublicoSerializer,
    SobreNosotrosEmpresaSerializer,
    SucursalEmpresaAdminSerializer,
    SucursalEmpresaPublicaSerializer,
)


class Conflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "La operacion no puede completarse por registros relacionados."
    default_code = "conflict"


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


class SobreNosotrosEmpresaPublicoView(EmpresaResolucionMixin, views.APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        empresa = self.resolver_empresa(request)
        modulo_activo = empresa.items_menu.filter(
            clave="sobre_nosotros",
            activo=True,
        ).exists()
        if not modulo_activo:
            raise NotFound("La pagina Sobre nosotros no esta activa para esta empresa.")

        contenido = SobreNosotrosEmpresa.objects.filter(empresa=empresa).first()
        if not contenido:
            raise NotFound("La empresa no tiene contenido de Sobre nosotros.")

        serializer = SobreNosotrosEmpresaPublicoSerializer(
            contenido,
            context={"request": request},
        )
        return response.Response(serializer.data)


class EmpresaViewSet(viewsets.ModelViewSet):
    queryset = Empresa.objects.all()
    serializer_class = EmpresaSerializer
    permission_classes = [IsSuperUser]

    def perform_create(self, serializer):
        serializer.save(creada_por=self.request.user)


class MiEmpresaView(views.APIView):
    permission_classes = [IsAuthenticated, IsAdministrativeUser]

    def get(self, request):
        empresa = obtener_empresa_administrable(request)
        serializer = EmpresaMiEmpresaSerializer(
            empresa,
            context={"request": request},
        )
        return response.Response(serializer.data)

    def patch(self, request):
        empresa = obtener_empresa_administrable(request)
        serializer = EmpresaMiEmpresaSerializer(
            empresa,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return response.Response(serializer.data)


class MiSobreNosotrosEmpresaView(views.APIView):
    permission_classes = [IsAuthenticated, IsAdministrativeUser]

    def get_contenido(self, request):
        empresa = obtener_empresa_administrable(request)
        contenido, _created = SobreNosotrosEmpresa.objects.get_or_create(
            empresa=empresa,
        )
        return contenido

    def get(self, request):
        serializer = SobreNosotrosEmpresaSerializer(
            self.get_contenido(request),
            context={"request": request},
        )
        return response.Response(serializer.data)

    def patch(self, request):
        serializer = SobreNosotrosEmpresaSerializer(
            self.get_contenido(request),
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return response.Response(serializer.data)


class ContextoAdministrativoView(views.APIView):
    permission_classes = [IsAuthenticated, IsAdministrativeUser]

    def get(self, request):
        empresa = obtener_empresa_administrable(request, requerida=False)
        perfil = getattr(request.user, "perfil", None)
        empresas = empresas_administrables(request.user).order_by("nombre")
        return response.Response(
            {
                "usuario": {
                    "id": request.user.id,
                    "username": request.user.username,
                    "email": request.user.email,
                    "nombre": request.user.get_full_name(),
                    "es_superusuario": request.user.is_superuser,
                },
                "perfil": (
                    PerfilUsuarioSerializer(perfil).data if perfil else None
                ),
                "empresa_actual": (
                    EmpresaMiEmpresaSerializer(
                        empresa,
                        context={"request": request},
                    ).data
                    if empresa
                    else None
                ),
                "empresas_disponibles": [
                    {
                        "id": item.id,
                        "nombre": item.nombre,
                        "slug": item.slug,
                        "activa": item.activa,
                    }
                    for item in empresas
                ],
                "permisos": {
                    "puede_crear_empresas": request.user.is_superuser,
                    "puede_configurar_dominios": request.user.is_superuser,
                    "puede_administrar_empresa_actual": empresa is not None,
                },
            }
        )


def _valor_booleano(query_params, nombre):
    return query_params.get(nombre, "").strip().lower() in ["true", "1", "si", "yes"]


def _valor_booleano_opcional(query_params, nombre):
    valor = query_params.get(nombre, "").strip().lower()
    if valor in ["true", "1", "si", "yes"]:
        return True
    if valor in ["false", "0", "no"]:
        return False
    return None


class ItemMenuEmpresaViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ItemMenuEmpresaAdminSerializer
    permission_classes = [IsAuthenticated, IsAdministrativeUser]
    pagination_class = PaginacionAdministrativa

    def get_empresa(self):
        if not hasattr(self, "_empresa_administrada"):
            self._empresa_administrada = obtener_empresa_administrable(self.request)
        return self._empresa_administrada

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["empresa"] = self.get_empresa()
        return context

    def get_queryset(self):
        queryset = ItemMenuEmpresa.objects.filter(
            empresa=self.get_empresa(),
        )
        if not _valor_booleano(self.request.query_params, "incluir_inactivos"):
            queryset = queryset.filter(activo=True)

        buscar = self.request.query_params.get("buscar", "").strip()
        if buscar:
            queryset = queryset.filter(
                Q(clave__icontains=buscar)
                | Q(texto__icontains=buscar)
                | Q(ruta__icontains=buscar)
            )

        orden = self.request.query_params.get("orden", "").strip()
        ordenes = {
            "orden": ("orden", "texto"),
            "-orden": ("-orden", "texto"),
            "texto": ("texto", "orden"),
            "-texto": ("-texto", "orden"),
            "clave": ("clave", "orden"),
        }
        return queryset.order_by(*ordenes.get(orden, ("orden", "texto")))

    def perform_update(self, serializer):
        serializer.save(empresa=self.get_empresa())


class CatalogoUbicacionMixin:
    pagination_class = PaginacionAdministrativa

    def get_permissions(self):
        if self.request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            return [IsSuperUser()]
        return [AllowAny()]

    def _es_usuario_administrativo(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return False
        return IsAdministrativeUser().has_permission(self.request, self)

    def paginate_queryset(self, queryset):
        paginar = _valor_booleano_opcional(self.request.query_params, "paginar")
        if paginar is not None:
            if paginar:
                return super().paginate_queryset(queryset)
            return None

        if self._es_usuario_administrativo():
            return super().paginate_queryset(queryset)
        return None


class DepartamentoViewSet(CatalogoUbicacionMixin, viewsets.ModelViewSet):
    serializer_class = DepartamentoSerializer

    def get_queryset(self):
        queryset = Departamento.objects.all()
        if not self._es_usuario_administrativo():
            queryset = queryset.filter(activo=True)
        else:
            activo = _valor_booleano_opcional(self.request.query_params, "activo")
            if activo is not None:
                queryset = queryset.filter(activo=activo)
            elif (
                self.action == "list"
                and not _valor_booleano(self.request.query_params, "incluir_inactivos")
            ):
                queryset = queryset.filter(activo=True)

        buscar = self.request.query_params.get("buscar", "").strip()
        if buscar:
            queryset = queryset.filter(nombre__icontains=buscar)

        orden = self.request.query_params.get("orden", "").strip()
        ordenes = {
            "orden": ("orden", "nombre"),
            "-orden": ("-orden", "nombre"),
            "nombre": ("nombre",),
            "-nombre": ("-nombre",),
        }
        return queryset.order_by(*ordenes.get(orden, ("orden", "nombre")))

    def perform_destroy(self, instance):
        if instance.municipios.exists():
            raise Conflict(
                "No se puede eliminar un departamento vinculado a municipios. "
                "Puedes desactivarlo."
            )
        instance.delete()


class MunicipioViewSet(CatalogoUbicacionMixin, viewsets.ModelViewSet):
    serializer_class = MunicipioSerializer

    def get_queryset(self):
        queryset = Municipio.objects.select_related("departamento")
        if not self._es_usuario_administrativo():
            queryset = queryset.filter(activo=True, departamento__activo=True)
        else:
            activo = _valor_booleano_opcional(self.request.query_params, "activo")
            if activo is not None:
                queryset = queryset.filter(activo=activo)
            elif (
                self.action == "list"
                and not _valor_booleano(self.request.query_params, "incluir_inactivos")
            ):
                queryset = queryset.filter(activo=True, departamento__activo=True)

        departamento_id = self.request.query_params.get("departamento_id", "").strip()
        if departamento_id:
            queryset = queryset.filter(departamento_id=departamento_id)

        departamento_codigo = self.request.query_params.get(
            "departamento_codigo",
            "",
        ).strip()
        if departamento_codigo:
            queryset = queryset.filter(departamento__codigo=departamento_codigo)

        buscar = self.request.query_params.get("buscar", "").strip()
        if buscar:
            queryset = queryset.filter(
                Q(nombre__icontains=buscar)
                | Q(departamento__nombre__icontains=buscar)
            )

        orden = self.request.query_params.get("orden", "").strip()
        ordenes = {
            "orden": ("departamento__orden", "orden", "nombre"),
            "-orden": ("departamento__orden", "-orden", "nombre"),
            "nombre": ("nombre",),
            "-nombre": ("-nombre",),
            "departamento": ("departamento__orden", "orden", "nombre"),
            "-departamento": ("-departamento__orden", "orden", "nombre"),
        }
        return queryset.order_by(
            *ordenes.get(orden, ("departamento__orden", "orden", "nombre"))
        )

    def perform_destroy(self, instance):
        if instance.sucursales.exists():
            raise Conflict(
                "No se puede eliminar un municipio vinculado a sucursales. "
                "Puedes desactivarlo."
            )
        instance.delete()


class SucursalEmpresaViewSet(viewsets.ModelViewSet):
    pagination_class = PaginacionAdministrativa

    def get_permissions(self):
        if self.request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            return [IsAuthenticated(), IsAdministrativeUser()]
        return [AllowAny()]

    def _es_usuario_administrativo(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return False
        return IsAdministrativeUser().has_permission(self.request, self)

    def get_serializer_class(self):
        if self._es_usuario_administrativo():
            return SucursalEmpresaAdminSerializer
        return SucursalEmpresaPublicaSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["empresa"] = self.get_empresa()
        return context

    def get_empresa(self):
        if self._es_usuario_administrativo():
            return obtener_empresa_administrable(self.request)

        empresa_slug = self.request.query_params.get("empresa_slug", "").strip()
        if not empresa_slug:
            raise ValidationError(
                {"empresa_slug": "Debes enviar el slug de la empresa."}
            )
        empresa = Empresa.objects.filter(
            slug__iexact=empresa_slug,
            activa=True,
        ).first()
        if not empresa:
            raise NotFound("La empresa no existe o no esta activa.")
        return empresa

    def get_queryset(self):
        queryset = SucursalEmpresa.objects.select_related(
            "empresa",
            "municipio",
            "municipio__departamento",
        ).filter(empresa=self.get_empresa())
        if not self._es_usuario_administrativo():
            queryset = queryset.filter(estado=SucursalEmpresa.Estado.ACTIVA)
        elif (
            self.action == "list"
            and not _valor_booleano(
                self.request.query_params,
                "incluir_inactivos",
            )
        ):
            queryset = queryset.filter(estado=SucursalEmpresa.Estado.ACTIVA)

        buscar = self.request.query_params.get("buscar", "").strip()
        if buscar:
            queryset = queryset.filter(
                Q(nombre__icontains=buscar)
                | Q(ciudad__icontains=buscar)
                | Q(municipio__nombre__icontains=buscar)
                | Q(municipio__departamento__nombre__icontains=buscar)
                | Q(direccion__icontains=buscar)
                | Q(telefono__icontains=buscar)
                | Q(horario__icontains=buscar)
            )

        estado = self.request.query_params.get("estado", "").strip()
        if estado and self._es_usuario_administrativo():
            queryset = queryset.filter(estado=estado)

        ciudad = self.request.query_params.get("ciudad", "").strip()
        if ciudad:
            queryset = queryset.filter(ciudad__iexact=ciudad)

        municipio = self.request.query_params.get("municipio", "").strip()
        if municipio:
            queryset = queryset.filter(municipio__nombre__iexact=municipio)

        municipio_id = self.request.query_params.get("municipio_id", "").strip()
        if municipio_id:
            queryset = queryset.filter(municipio_id=municipio_id)

        departamento_id = self.request.query_params.get(
            "departamento_id",
            "",
        ).strip()
        if departamento_id:
            queryset = queryset.filter(municipio__departamento_id=departamento_id)

        orden = self.request.query_params.get("orden", "").strip()
        ordenes = {
            "orden": ("orden", "nombre"),
            "-orden": ("-orden", "nombre"),
            "nombre": ("nombre",),
            "-nombre": ("-nombre",),
            "municipio": ("municipio__nombre", "orden", "nombre"),
            "-municipio": ("-municipio__nombre", "orden", "nombre"),
            "departamento": (
                "municipio__departamento__orden",
                "municipio__nombre",
                "orden",
                "nombre",
            ),
            "-departamento": (
                "-municipio__departamento__orden",
                "municipio__nombre",
                "orden",
                "nombre",
            ),
            "ciudad": ("ciudad", "nombre"),
            "-ciudad": ("-ciudad", "nombre"),
        }
        return queryset.order_by(*ordenes.get(orden, ("orden", "nombre")))

    def paginate_queryset(self, queryset):
        if not self._es_usuario_administrativo():
            return None
        return super().paginate_queryset(queryset)

    def perform_create(self, serializer):
        serializer.save(empresa=self.get_empresa())

    def perform_update(self, serializer):
        serializer.save(empresa=self.get_empresa())

    def perform_destroy(self, instance):
        instance.estado = SucursalEmpresa.Estado.INACTIVA
        instance.activa = False
        instance.save(update_fields=["estado", "activa", "fecha_actualizacion"])


class SucursalesZonasView(EmpresaResolucionMixin, views.APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        empresa = self.resolver_empresa(request)
        queryset = (
            SucursalEmpresa.objects.select_related(
                "empresa",
                "municipio",
                "municipio__departamento",
            )
            .filter(
                empresa=empresa,
                estado=SucursalEmpresa.Estado.ACTIVA,
                municipio__isnull=False,
                municipio__activo=True,
                municipio__departamento__activo=True,
            )
            .order_by(
                "municipio__departamento__orden",
                "municipio__departamento__nombre",
                "municipio__orden",
                "municipio__nombre",
                "orden",
                "nombre",
            )
        )

        buscar = request.query_params.get("buscar", "").strip()
        if buscar:
            queryset = queryset.filter(
                Q(nombre__icontains=buscar)
                | Q(ciudad__icontains=buscar)
                | Q(municipio__nombre__icontains=buscar)
                | Q(municipio__departamento__nombre__icontains=buscar)
                | Q(direccion__icontains=buscar)
            )

        departamentos = {}
        serializer_context = {"request": request}
        for sucursal in queryset:
            departamento = sucursal.municipio.departamento
            departamento_data = departamentos.setdefault(
                departamento.pk,
                {
                    "departamento_id": departamento.pk,
                    "departamento": departamento.nombre,
                    "departamento_codigo": departamento.codigo,
                    "total_sucursales": 0,
                    "municipios": {},
                },
            )
            municipio_data = departamento_data["municipios"].setdefault(
                sucursal.municipio_id,
                {
                    "municipio_id": sucursal.municipio_id,
                    "municipio": sucursal.municipio.nombre,
                    "total_sucursales": 0,
                    "sucursales": [],
                },
            )
            sucursal_data = SucursalEmpresaPublicaSerializer(
                sucursal,
                context=serializer_context,
            ).data
            municipio_data["sucursales"].append(sucursal_data)
            municipio_data["total_sucursales"] += 1
            departamento_data["total_sucursales"] += 1

        data = []
        for departamento_data in departamentos.values():
            departamento_data["municipios"] = list(
                departamento_data["municipios"].values()
            )
            data.append(departamento_data)

        return response.Response(data)


class SucursalesCercanasView(EmpresaResolucionMixin, views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        empresa = self.resolver_empresa(request)
        perfil = getattr(request.user, "perfil", None)
        municipio = getattr(perfil, "municipio", None)

        if not municipio:
            return response.Response(
                {
                    "municipio_id": None,
                    "municipio": None,
                    "departamento_id": None,
                    "departamento": None,
                    "sucursales_municipio": [],
                    "sucursales_departamento": [],
                }
            )

        queryset = SucursalEmpresa.objects.select_related(
            "empresa",
            "municipio",
            "municipio__departamento",
        ).filter(
            empresa=empresa,
            estado=SucursalEmpresa.Estado.ACTIVA,
            municipio__isnull=False,
        )
        sucursales_municipio = queryset.filter(municipio=municipio).order_by(
            "orden",
            "nombre",
        )
        sucursales_departamento = (
            queryset.filter(municipio__departamento=municipio.departamento)
            .exclude(municipio=municipio)
            .order_by("municipio__orden", "municipio__nombre", "orden", "nombre")
        )
        serializer_context = {"request": request}

        return response.Response(
            {
                "municipio_id": municipio.pk,
                "municipio": municipio.nombre,
                "departamento_id": municipio.departamento_id,
                "departamento": municipio.departamento.nombre,
                "sucursales_municipio": SucursalEmpresaPublicaSerializer(
                    sucursales_municipio,
                    many=True,
                    context=serializer_context,
                ).data,
                "sucursales_departamento": SucursalEmpresaPublicaSerializer(
                    sucursales_departamento,
                    many=True,
                    context=serializer_context,
                ).data,
            }
        )
