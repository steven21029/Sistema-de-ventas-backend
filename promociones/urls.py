from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BannerPromocionalViewSet, OfertaPromocionalViewSet

router = DefaultRouter()
router.register(
    "promociones/banners",
    BannerPromocionalViewSet,
    basename="promociones-banners",
)
router.register(
    "promociones/ofertas",
    OfertaPromocionalViewSet,
    basename="promociones-ofertas",
)

urlpatterns = [
    path("", include(router.urls)),
]
