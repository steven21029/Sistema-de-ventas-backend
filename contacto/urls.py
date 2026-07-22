from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import MensajeContactoViewSet

router = DefaultRouter()
router.register("contacto/mensajes", MensajeContactoViewSet, basename="contacto-mensajes")

urlpatterns = [
    path("", include(router.urls)),
]
