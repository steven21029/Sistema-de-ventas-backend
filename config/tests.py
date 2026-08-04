from django.test import SimpleTestCase
from django.urls import resolve, reverse


class ApiVersionCompatibilityTests(SimpleTestCase):
    def test_empresa_actual_acepta_ruta_versionada(self):
        match = resolve("/api/v1/empresas/actual/")

        self.assertEqual(match.url_name, "empresas-actual")

    def test_refresh_acepta_ruta_versionada(self):
        match = resolve("/api/v1/usuarios/token/refresh/")

        self.assertEqual(match.url_name, "usuarios-token-refresh")

    def test_reverse_conserva_ruta_sin_version(self):
        self.assertEqual(reverse("empresas-actual"), "/api/empresas/actual/")
