from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def healthcheck(_request):
    return JsonResponse({"estado": "ok"})
