from rest_framework import response, views, viewsets
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny

from .models import Empresa
from .permissions import IsSuperUser
from .serializers import EmpresaPublicaSerializer, EmpresaSerializer


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
