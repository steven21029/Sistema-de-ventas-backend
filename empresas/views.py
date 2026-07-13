from rest_framework import viewsets

from .models import Empresa
from .permissions import IsSuperUser
from .serializers import EmpresaSerializer


class EmpresaViewSet(viewsets.ModelViewSet):
    queryset = Empresa.objects.all()
    serializer_class = EmpresaSerializer
    permission_classes = [IsSuperUser]

    def perform_create(self, serializer):
        serializer.save(creada_por=self.request.user)
