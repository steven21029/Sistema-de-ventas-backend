import hashlib
import hmac
import json

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import override_settings
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from catalogo.models import Categoria, Familia, Producto
from empresas.models import Empresa
from inventario.models import MovimientoInventario
from pedidos.models import Carrito, ItemCarrito, Pedido, Prefactura
from usuarios.models import PerfilUsuario

from .models import EventoWebhookPago, Pago


@override_settings(
    PAGOS_PROVEEDOR_DEFAULT="proveedor_prueba",
    PAGOS_WEBHOOK_SECRET="secreto-webhook-pruebas",
)
class PagosAPITests(APITestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Empresa pagos",
            slug="empresa-pagos",
            modo_inventario=Empresa.ModoInventario.MIXTO,
        )
        familia = Familia.objects.create(
            empresa=self.empresa,
            nombre="Productos",
        )
        categoria = Categoria.objects.create(
            empresa=self.empresa,
            familia=familia,
            nombre="Fisicos",
        )
        self.producto = Producto.objects.create(
            empresa=self.empresa,
            familia=familia,
            categoria=categoria,
            tipo_item=Producto.TipoItem.PRODUCTO_FISICO,
            codigo_barra="PAGO-FISICO-001",
            nombre="Producto pagable",
            precio="100.00",
        )
        Producto.objects.filter(pk=self.producto.pk).update(existencia=3)
        self.producto.refresh_from_db()
        self.usuario = self._crear_usuario("cliente-pagos@example.com")
        self.client.force_authenticate(self.usuario)
        carrito = Carrito.objects.create(
            empresa=self.empresa,
            usuario=self.usuario,
        )
        ItemCarrito.objects.create(
            carrito=carrito,
            producto=self.producto,
            cantidad=2,
        )
        self.pedido = Pedido.generar_desde_carrito(
            carrito=carrito,
            tipo_entrega=Pedido.TipoEntrega.RETIRO_EN_LOCAL,
        )

    def _crear_usuario(self, correo):
        usuario = get_user_model().objects.create_user(
            username=correo,
            email=correo,
            password="ClaveSegura123!",
        )
        usuario.perfil.empresa = self.empresa
        usuario.perfil.rol = PerfilUsuario.Rol.COMPRADOR
        usuario.perfil.activo = True
        usuario.perfil.correo_verificado = True
        usuario.perfil.save()
        return usuario

    def _iniciar_pago(self, datos_extra=None):
        datos = {"pedido_id": self.pedido.pk}
        datos.update(datos_extra or {})
        return self.client.post(
            reverse("pagos-iniciar"),
            datos,
            format="json",
        )

    def _enviar_webhook(self, payload, firma_valida=True):
        cuerpo = json.dumps(payload, separators=(",", ":"))
        firma = hmac.new(
            b"secreto-webhook-pruebas",
            cuerpo.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not firma_valida:
            firma = "firma-invalida"
        return self.client.post(
            reverse(
                "pagos-webhook",
                kwargs={"proveedor": "proveedor_prueba"},
            ),
            data=cuerpo,
            content_type="application/json",
            HTTP_X_PAGO_SIGNATURE=f"sha256={firma}",
        )

    def _payload(self, pago, estado=Pago.Estado.APROBADO, evento_id="evt-001"):
        return {
            "evento_id": evento_id,
            "referencia": str(pago.referencia),
            "estado": estado,
            "identificador_externo": f"ext-{evento_id}",
            "codigo_respuesta": "00" if estado == Pago.Estado.APROBADO else "05",
        }

    def test_inicio_toma_monto_del_pedido_y_es_idempotente(self):
        primera = self._iniciar_pago({"monto": "0.01", "moneda": "USD"})
        segunda = self._iniciar_pago()

        self.assertEqual(primera.status_code, status.HTTP_201_CREATED)
        self.assertEqual(segunda.status_code, status.HTTP_200_OK)
        self.assertEqual(primera.data["referencia"], segunda.data["referencia"])
        self.assertEqual(primera.data["monto"], f"{self.pedido.total:.2f}")
        self.assertEqual(primera.data["moneda"], self.pedido.moneda)
        self.assertEqual(Pago.objects.filter(pedido=self.pedido).count(), 1)

    def test_webhook_con_firma_invalida_no_modifica_el_pago(self):
        pago = Pago.objects.get(referencia=self._iniciar_pago().data["referencia"])
        respuesta = self._enviar_webhook(self._payload(pago), firma_valida=False)

        pago.refresh_from_db()
        self.pedido.refresh_from_db()
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(pago.estado, Pago.Estado.PENDIENTE)
        self.assertEqual(self.pedido.estado_pago, Pedido.EstadoPago.PENDIENTE)
        self.assertFalse(EventoWebhookPago.objects.exists())

    def test_webhook_aprueba_una_vez_y_completa_el_pedido(self):
        pago = Pago.objects.get(referencia=self._iniciar_pago().data["referencia"])
        payload = self._payload(pago)

        primera = self._enviar_webhook(payload)
        segunda = self._enviar_webhook(payload)

        pago.refresh_from_db()
        self.pedido.refresh_from_db()
        self.producto.refresh_from_db()
        self.assertEqual(primera.status_code, status.HTTP_200_OK)
        self.assertFalse(primera.data["duplicado"])
        self.assertEqual(segunda.status_code, status.HTTP_200_OK)
        self.assertTrue(segunda.data["duplicado"])
        self.assertEqual(pago.estado, Pago.Estado.APROBADO)
        self.assertEqual(self.pedido.estado_pago, Pedido.EstadoPago.PAGADO)
        self.assertTrue(self.pedido.inventario_descontado)
        self.assertEqual(self.producto.existencia, 1)
        self.assertTrue(Prefactura.objects.filter(pedido=self.pedido).exists())
        self.assertEqual(
            MovimientoInventario.objects.filter(referencia=self.pedido.numero).count(),
            1,
        )
        self.assertEqual(EventoWebhookPago.objects.filter(procesado=True).count(), 1)

    def test_rechazo_deja_pedido_pendiente_y_permite_nuevo_intento(self):
        pago = Pago.objects.get(referencia=self._iniciar_pago().data["referencia"])
        rechazo = self._enviar_webhook(
            self._payload(
                pago,
                estado=Pago.Estado.RECHAZADO,
                evento_id="evt-rechazado",
            )
        )
        nuevo = self._iniciar_pago()

        pago.refresh_from_db()
        self.pedido.refresh_from_db()
        self.assertEqual(rechazo.status_code, status.HTTP_200_OK)
        self.assertEqual(pago.estado, Pago.Estado.RECHAZADO)
        self.assertEqual(self.pedido.estado_pago, Pedido.EstadoPago.PENDIENTE)
        self.assertEqual(nuevo.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(str(pago.referencia), nuevo.data["referencia"])
        self.assertEqual(Pago.objects.filter(pedido=self.pedido).count(), 2)

    def test_evento_repetido_con_otro_contenido_se_rechaza(self):
        pago = Pago.objects.get(referencia=self._iniciar_pago().data["referencia"])
        payload = self._payload(pago, evento_id="evt-repetido")
        primera = self._enviar_webhook(payload)
        payload["identificador_externo"] = "externo-alterado"
        segunda = self._enviar_webhook(payload)

        self.assertEqual(primera.status_code, status.HTTP_200_OK)
        self.assertEqual(segunda.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("evento_id", segunda.data)

    def test_otro_cliente_no_puede_iniciar_ni_ver_el_pago(self):
        pago = Pago.objects.get(referencia=self._iniciar_pago().data["referencia"])
        otro_usuario = self._crear_usuario("otro-cliente-pagos@example.com")
        self.client.force_authenticate(otro_usuario)

        iniciar = self._iniciar_pago()
        detalle = self.client.get(
            reverse("pagos-detail", args=[pago.referencia]),
        )
        listado = self.client.get(reverse("pagos-list"))

        self.assertEqual(iniciar.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(detalle.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(listado.status_code, status.HTTP_200_OK)
        self.assertEqual(listado.data, [])

    def test_estado_no_puede_cambiarse_directamente(self):
        pago = Pago.objects.get(referencia=self._iniciar_pago().data["referencia"])
        pago.estado = Pago.Estado.APROBADO

        with self.assertRaises(ValidationError):
            pago.save()
        with self.assertRaises(ValidationError):
            pago.delete()

        respuesta = self.client.patch(
            reverse("pagos-detail", args=[pago.referencia]),
            {"estado": Pago.Estado.APROBADO},
            format="json",
        )
        self.assertEqual(respuesta.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
