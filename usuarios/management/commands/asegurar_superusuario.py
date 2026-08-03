import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from usuarios.models import PerfilUsuario


class Command(BaseCommand):
    help = "Crea o actualiza el superusuario definido en variables de entorno."

    VARIABLES = (
        "DJANGO_SUPERUSER_USERNAME",
        "DJANGO_SUPERUSER_EMAIL",
        "DJANGO_SUPERUSER_PASSWORD",
    )

    def handle(self, *args, **options):
        valores = {
            nombre: os.environ.get(nombre, "").strip()
            for nombre in self.VARIABLES
        }
        faltantes = [nombre for nombre, valor in valores.items() if not valor]
        if faltantes:
            raise CommandError(
                "Faltan variables para crear el superusuario: "
                + ", ".join(faltantes)
            )

        username = valores["DJANGO_SUPERUSER_USERNAME"]
        email = valores["DJANGO_SUPERUSER_EMAIL"]
        password = valores["DJANGO_SUPERUSER_PASSWORD"]
        User = get_user_model()

        user = User.objects.filter(username=username).first()
        creado = user is None
        if creado:
            user = User(username=username)

        user.email = email
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True

        try:
            validate_password(password, user=user)
        except ValidationError as exc:
            raise CommandError(
                "DJANGO_SUPERUSER_PASSWORD no cumple la seguridad requerida: "
                + " ".join(exc.messages)
            ) from exc

        user.set_password(password)

        with transaction.atomic():
            user.save()
            perfil, _created = PerfilUsuario.objects.get_or_create(usuario=user)
            perfil.rol = PerfilUsuario.Rol.ADMINISTRADOR_MAESTRO
            perfil.empresa = None
            perfil.correo_verificado = True
            perfil.puede_crear_usuarios = True
            perfil.activo = True
            perfil.save(
                update_fields=[
                    "rol",
                    "empresa",
                    "correo_verificado",
                    "puede_crear_usuarios",
                    "activo",
                    "fecha_actualizacion",
                ]
            )

        accion = "creado" if creado else "actualizado"
        self.stdout.write(
            self.style.SUCCESS(f"Superusuario '{username}' {accion} correctamente.")
        )
