from django.test import SimpleTestCase
from django.urls import reverse


class HealthcheckTests(SimpleTestCase):
    def test_healthcheck_publico(self):
        respuesta = self.client.get(reverse("healthcheck"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json(), {"estado": "ok"})
