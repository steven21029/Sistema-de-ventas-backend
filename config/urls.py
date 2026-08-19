"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

from .health import healthcheck

urlpatterns = [
    path('health/', healthcheck, name='healthcheck'),
    path('admin/', admin.site.urls),
    path('api/v1/', include('empresas.urls')),
    path('api/v1/', include('usuarios.urls')),
    path('api/v1/', include('catalogo.urls')),
    path('api/v1/', include('inventario.urls')),
    path('api/v1/', include('pedidos.urls')),
    path('api/v1/', include('pagos.urls')),
    path('api/v1/', include('favoritos.urls')),
    path('api/v1/', include('promociones.urls')),
    path('api/v1/', include('contacto.urls')),
    path('api/v1/', include('reportes.urls')),
    path('api/', include('empresas.urls')),
    path('api/', include('usuarios.urls')),
    path('api/', include('catalogo.urls')),
    path('api/', include('inventario.urls')),
    path('api/', include('pedidos.urls')),
    path('api/', include('pagos.urls')),
    path('api/', include('favoritos.urls')),
    path('api/', include('promociones.urls')),
    path('api/', include('contacto.urls')),
    path('api/', include('reportes.urls')),
]

if settings.DEBUG and not settings.R2_STORAGE_ENABLED:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
