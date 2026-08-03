from rest_framework.exceptions import NotFound, PermissionDenied

from .models import Empresa


def obtener_empresa_actual(request):
    empresa = getattr(request, "empresa_actual", None)
    if empresa:
        return empresa

    slug = (
        request.query_params.get("empresa_slug", "").strip()
        or request.query_params.get("slug", "").strip()
    )
    if not slug:
        return None

    return Empresa.objects.filter(slug__iexact=slug, activa=True).first()


def obtener_empresa_administrable(request, requerida=True):
    user = request.user
    if not user or not user.is_authenticated:
        raise PermissionDenied("Debes iniciar sesion para administrar una empresa.")

    empresa_solicitada = obtener_empresa_actual(request)
    perfil = getattr(user, "perfil", None)

    if user.is_superuser:
        if requerida and not empresa_solicitada:
            raise NotFound("No se pudo determinar la empresa actual.")
        return empresa_solicitada

    if not perfil or not perfil.activo:
        raise PermissionDenied("Tu perfil administrativo no esta activo.")

    if perfil.es_administrador_empresa or perfil.es_gerente:
        if not perfil.empresa_id:
            raise PermissionDenied("Tu perfil no tiene una empresa asignada.")
        if empresa_solicitada and empresa_solicitada.pk != perfil.empresa_id:
            raise PermissionDenied("No puedes administrar otra empresa.")
        return perfil.empresa

    if perfil.es_administrador_maestro:
        if not empresa_solicitada:
            if requerida:
                raise NotFound("Debes seleccionar una empresa permitida.")
            return None

        empresa_permitida = perfil.empresas_permitidas.filter(
            pk=empresa_solicitada.pk,
        ).exists()
        if perfil.empresa_id == empresa_solicitada.pk:
            empresa_permitida = True
        if not empresa_permitida:
            raise PermissionDenied("No tienes permiso para administrar esta empresa.")
        return empresa_solicitada

    raise PermissionDenied("Los compradores no tienen acceso administrativo.")


def empresas_administrables(user):
    if user.is_superuser:
        return Empresa.objects.all()

    perfil = getattr(user, "perfil", None)
    if not perfil or not perfil.activo:
        return Empresa.objects.none()
    if perfil.es_administrador_maestro:
        queryset = perfil.empresas_permitidas.all()
        if perfil.empresa_id:
            queryset = (queryset | Empresa.objects.filter(pk=perfil.empresa_id)).distinct()
        return queryset
    if perfil.empresa_id and (perfil.es_administrador_empresa or perfil.es_gerente):
        return Empresa.objects.filter(pk=perfil.empresa_id)
    return Empresa.objects.none()
