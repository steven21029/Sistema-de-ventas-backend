from .models import Empresa


class EmpresaContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path_info == "/health/":
            request.empresa_actual = None
            return self.get_response(request)

        request.empresa_actual = self._resolver_empresa(request)
        return self.get_response(request)

    def _resolver_empresa(self, request):
        host = (
            request.GET.get("host", "").strip()
            or request.headers.get("X-Frontend-Host", "").strip()
            or request.get_host()
        )
        empresa = Empresa.resolver_por_host(host)
        if empresa:
            return empresa

        slug = (
            request.GET.get("empresa_slug", "").strip()
            or request.GET.get("slug", "").strip()
        )
        if not slug:
            return None

        return Empresa.objects.filter(slug__iexact=slug, activa=True).first()
