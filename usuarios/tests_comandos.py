import os
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from .models import PerfilUsuario


User = get_user_model()


class AsegurarSuperusuarioCommandTests(TestCase):
    VARIABLES = {
        "DJANGO_SUPERUSER_USERNAME": "admin-render",
        "DJANGO_SUPERUSER_EMAIL": "admin-render@example.com",
        "DJANGO_SUPERUSER_PASSWORD": "Render-Admin-2026!Clave",
    }

    def ejecutar(self, variables=None):
        entorno = self.VARIABLES if variables is None else variables
        salida = StringIO()
        with patch.dict(os.environ, entorno, clear=True):
            call_command("asegurar_superusuario", stdout=salida)
        return salida.getvalue()

    def test_crea_superusuario_y_perfil_maestro_verificado(self):
        salida = self.ejecutar()

        user = User.objects.get(username="admin-render")
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_active)
        self.assertTrue(user.check_password("Render-Admin-2026!Clave"))
        self.assertEqual(
            user.perfil.rol,
            PerfilUsuario.Rol.ADMINISTRADOR_MAESTRO,
        )
        self.assertTrue(user.perfil.correo_verificado)
        self.assertTrue(user.perfil.puede_crear_usuarios)
        self.assertIn("creado correctamente", salida)

    def test_es_idempotente_y_actualiza_la_contrasena(self):
        self.ejecutar()
        nuevas_variables = {
            **self.VARIABLES,
            "DJANGO_SUPERUSER_PASSWORD": "Render-Admin-2026!Nueva",
        }

        salida = self.ejecutar(nuevas_variables)

        self.assertEqual(User.objects.filter(username="admin-render").count(), 1)
        user = User.objects.get(username="admin-render")
        self.assertTrue(user.check_password("Render-Admin-2026!Nueva"))
        self.assertIn("actualizado correctamente", salida)

    def test_rechaza_variables_incompletas(self):
        with self.assertRaisesMessage(
            CommandError,
            "DJANGO_SUPERUSER_PASSWORD",
        ):
            self.ejecutar(
                {
                    "DJANGO_SUPERUSER_USERNAME": "admin-render",
                    "DJANGO_SUPERUSER_EMAIL": "admin-render@example.com",
                }
            )

    def test_rechaza_contrasena_debil(self):
        variables = {
            **self.VARIABLES,
            "DJANGO_SUPERUSER_PASSWORD": "0000",
        }

        with self.assertRaisesMessage(CommandError, "seguridad requerida"):
            self.ejecutar(variables)
