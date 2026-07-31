from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PagoViewSet, WebhookPagoView


router = DefaultRouter()
router.register("pagos", PagoViewSet, basename="pagos")

urlpatterns = [
    path(
        "pagos/webhooks/<str:proveedor>/",
        WebhookPagoView.as_view(),
        name="pagos-webhook",
    ),
    path("", include(router.urls)),
]
