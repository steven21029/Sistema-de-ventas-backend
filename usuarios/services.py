from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)


def revocar_sesiones_usuario(usuario):
    tokens = OutstandingToken.objects.filter(user=usuario)
    for token in tokens:
        BlacklistedToken.objects.get_or_create(token=token)
