from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import FavoritoViewSet

router = DefaultRouter()
router.register("favoritos", FavoritoViewSet, basename="favoritos")

urlpatterns = [
    path("", include(router.urls)),
]
