import re
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase
from PIL import Image as PILImage, ImageDraw

from catalogo.models import Categoria, Familia, Producto
from empresas.models import Empresa, SucursalEmpresa
from inventario.models import MovimientoInventario
from pedidos.models import Carrito, DetallePedido, ItemCarrito, Pedido, Prefactura
from usuarios.models import PerfilUsuario

from .models import Pago


User = get_user_model()


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    PAGOS_PROVEEDOR_DEFAULT="proveedor_prueba",
    PREFACTURA_MAX_INTENTOS_CORREO=3,
    PREFACTURA_VIGENCIA_HORAS=48,
)
class PagoEnSucursalAPITests(APITestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Empresa sucursal",
            slug="empresa-sucursal",
            modo_inventario=Empresa.ModoInventario.MIXTO,
        )
        self.otra_empresa = Empresa.objects.create(
            nombre="Otra empresa sucursal",
            slug="otra-empresa-sucursal",
            modo_inventario=Empresa.ModoInventario.MIXTO,
        )
        self.sucursal = SucursalEmpresa.objects.create(
            empresa=self.empresa,
            nombre="Sucursal Centro",
            direccion="Avenida principal",
        )
        self.sucursal_inactiva = SucursalEmpresa.objects.create(
            empresa=self.empresa,
            nombre="Sucursal cerrada",
            direccion="Calle secundaria",
            activa=False,
        )
        self.sucursal_otra = SucursalEmpresa.objects.create(
            empresa=self.otra_empresa,
            nombre="Sucursal ajena",
            direccion="Otra ciudad",
        )
        familia = Familia.objects.create(empresa=self.empresa, nombre="Productos")
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
            codigo_barra="SUC-001",
            nombre="Producto para sucursal",
            precio="100.00",
        )
        Producto.objects.filter(pk=self.producto.pk).update(existencia=5)
        self.producto.refresh_from_db()

        self.comprador = self._crear_usuario(
            "cliente-sucursal@example.com",
            PerfilUsuario.Rol.COMPRADOR,
            self.empresa,
        )
        self.otro_comprador = self._crear_usuario(
            "otro-cliente@example.com",
            PerfilUsuario.Rol.COMPRADOR,
            self.empresa,
        )
        self.admin = self._crear_usuario(
            "admin-sucursal@example.com",
            PerfilUsuario.Rol.ADMINISTRADOR_EMPRESA,
            self.empresa,
        )
        self.gerente = self._crear_usuario(
            "gerente-sucursal@example.com",
            PerfilUsuario.Rol.GERENTE,
            self.empresa,
        )
        self.admin_otra = self._crear_usuario(
            "admin-otra-sucursal@example.com",
            PerfilUsuario.Rol.ADMINISTRADOR_EMPRESA,
            self.otra_empresa,
        )
        self.pedido = self._crear_pedido(self.comprador)
        self.client.force_authenticate(self.comprador)

    def _crear_usuario(self, correo, rol, empresa, verificado=True):
        usuario = User.objects.create_user(
            username=correo,
            email=correo,
            password="ClaveSegura123!",
        )
        perfil = usuario.perfil
        perfil.empresa = empresa
        perfil.rol = rol
        perfil.activo = True
        perfil.correo_verificado = verificado
        perfil.save()
        return usuario

    def _crear_pedido(self, usuario):
        carrito = Carrito.objects.create(
            empresa=self.empresa,
            usuario=usuario,
        )
        ItemCarrito.objects.create(
            carrito=carrito,
            producto=self.producto,
            cantidad=2,
        )
        return Pedido.generar_desde_carrito(
            carrito=carrito,
            tipo_entrega=Pedido.TipoEntrega.RETIRO_EN_LOCAL,
        )

    def _pago_sucursal(self, pedido=None, sucursal=None):
        pedido_id = (pedido or self.pedido).pk
        return self.client.post(
            f"/api/v1/pedidos/pedidos/{pedido_id}/pago-en-sucursal/",
            {"sucursal_id": (sucursal or self.sucursal).pk},
            format="json",
        )

    def test_crea_pago_prefactura_pdf_y_correo_sin_descontar_inventario(self):
        respuesta = self._pago_sucursal()

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.pedido.refresh_from_db()
        self.producto.refresh_from_db()
        pago = Pago.objects.get(pedido=self.pedido)
        prefactura = Prefactura.objects.get(pedido=self.pedido)
        self.assertEqual(self.pedido.estado_pago, Pedido.EstadoPago.PENDIENTE)
        self.assertEqual(self.pedido.metodo_pago, Pedido.MetodoPago.SUCURSAL)
        self.assertEqual(self.pedido.sucursal_pago, self.sucursal)
        self.assertFalse(self.pedido.inventario_descontado)
        self.assertEqual(self.producto.existencia, 5)
        self.assertFalse(MovimientoInventario.objects.exists())
        self.assertEqual(pago.proveedor, "sucursal")
        self.assertEqual(pago.metodo, Pago.Metodo.SUCURSAL)
        self.assertEqual(pago.estado, Pago.Estado.PENDIENTE)
        self.assertEqual(prefactura.intentos_correo, 1)
        self.assertIsNotNone(prefactura.correo_enviado_en)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.comprador.email])
        self.assertEqual(mail.outbox[0].attachments[0].mimetype, "application/pdf")
        self.assertTrue(mail.outbox[0].attachments[0].content.startswith(b"%PDF"))
        self.assertEqual(respuesta.data["pedido"]["metodo_pago"], "sucursal")
        self.assertEqual(respuesta.data["pago"]["metodo"], "sucursal")
        self.assertTrue(respuesta.data["prefactura"]["correo_enviado"])
        self.assertEqual(
            respuesta.data["prefactura"]["url_pdf"],
            f"/api/v1/pedidos/pedidos/{self.pedido.pk}/prefactura/pdf/",
        )
        self.assertEqual(
            respuesta.data["prefactura"]["correo_destino"],
            "c***@example.com",
        )
        descarga = self.client.get(
            reverse("pedidos-pedidos-prefactura-pdf", args=[self.pedido.pk])
        )
        self.assertEqual(
            mail.outbox[0].attachments[0].content,
            descarga.content,
        )

    def test_solicitud_repetida_es_idempotente_y_no_reenvia_correo(self):
        primera = self._pago_sucursal()
        segunda = self._pago_sucursal()

        self.assertEqual(primera.status_code, status.HTTP_201_CREATED)
        self.assertEqual(segunda.status_code, status.HTTP_200_OK)
        self.assertEqual(
            primera.data["pago"]["referencia"],
            segunda.data["pago"]["referencia"],
        )
        self.assertEqual(
            primera.data["prefactura"]["numero"],
            segunda.data["prefactura"]["numero"],
        )
        self.assertEqual(Pago.objects.filter(pedido=self.pedido).count(), 1)
        self.assertEqual(Prefactura.objects.filter(pedido=self.pedido).count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(Prefactura.objects.get(pedido=self.pedido).intentos_correo, 1)

    def test_rechaza_sucursal_inactiva_o_de_otra_empresa(self):
        inactiva = self._pago_sucursal(sucursal=self.sucursal_inactiva)
        ajena = self._pago_sucursal(sucursal=self.sucursal_otra)

        self.assertEqual(inactiva.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ajena.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Pago.objects.filter(pedido=self.pedido).exists())
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.metodo_pago, Pedido.MetodoPago.PENDIENTE)

    def test_comprador_no_puede_gestionar_pedido_ajeno(self):
        self.client.force_authenticate(self.otro_comprador)
        respuesta = self._pago_sucursal()

        self.assertEqual(respuesta.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(Pago.objects.filter(pedido=self.pedido).exists())

    def test_exige_correo_verificado(self):
        no_verificado = self._crear_usuario(
            "sin-verificar@example.com",
            PerfilUsuario.Rol.COMPRADOR,
            self.empresa,
            verificado=False,
        )
        pedido = self._crear_pedido(no_verificado)
        self.client.force_authenticate(no_verificado)
        respuesta = self._pago_sucursal(pedido=pedido)

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("correo", respuesta.data)
        self.assertFalse(Pago.objects.filter(pedido=pedido).exists())

    def test_descarga_pdf_con_nombre_y_leyenda(self):
        self._pago_sucursal()
        respuesta = self.client.get(
            reverse("pedidos-pedidos-prefactura-pdf", args=[self.pedido.pk])
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta["Content-Type"], "application/pdf")
        self.assertEqual(
            respuesta["Content-Disposition"],
            f'attachment; filename="prefactura-{self.pedido.numero}.pdf"',
        )
        self.assertTrue(respuesta.content.startswith(b"%PDF"))
        self.assertIn(b"PREFACTURA", respuesta.content)

    def test_pdf_a4_usa_identidad_empresa_comprador_y_totales_oficiales(self):
        self.empresa.nombre = "Empresa Dinamica"
        self.empresa.telefono = "22334455"
        self.empresa.correo = "ventas@empresa.test"
        self.empresa.direccion = "Boulevard comercial 123"
        self.empresa.sitio_web = "https://empresa.test"
        self.empresa.color_principal = "#A51D2D"
        self.empresa.color_secundario = "#D5A021"
        self.empresa.color_acento = "#1F5A4A"
        self.empresa.save()

        self.comprador.first_name = "Maria"
        self.comprador.last_name = "Lopez"
        self.comprador.save(update_fields=["first_name", "last_name"])
        perfil = self.comprador.perfil
        perfil.numero_identidad = "0801199012345"
        perfil.telefono = "99887766"
        perfil.save(update_fields=["numero_identidad", "telefono"])

        detalle = self.pedido.detalles.get()
        DetallePedido.objects.filter(pk=detalle.pk).update(
            precio_unitario=Decimal("100.00"),
            cantidad=2,
            subtotal=Decimal("200.00"),
            porcentaje_descuento=10,
            descuento_unitario=Decimal("10.00"),
            precio_unitario_final=Decimal("90.00"),
            descuento_total=Decimal("20.00"),
            subtotal_final=Decimal("180.00"),
        )
        Pedido.objects.filter(pk=self.pedido.pk).update(
            subtotal=Decimal("200.00"),
            descuento_total=Decimal("20.00"),
            impuesto=Decimal("27.00"),
            envio=Decimal("25.00"),
            total=Decimal("232.00"),
        )
        self.pedido.refresh_from_db()

        self._pago_sucursal()
        respuesta = self.client.get(
            reverse("pedidos-pedidos-prefactura-pdf", args=[self.pedido.pk])
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertRegex(
            respuesta.content,
            rb"/MediaBox\s*\[\s*0\s+0\s+595\.2756\s+841\.8898\s*\]",
        )
        for texto in (
            b"Empresa Dinamica",
            b"22334455",
            b"ventas@empresa.test",
            b"Boulevard comercial 123",
            b"Maria Lopez",
            b"0801199012345",
            b"99887766",
            b"HNL 200.00",
            b"HNL 20.00",
            b"HNL 27.00",
            b"HNL 25.00",
            b"HNL 232.00",
        ):
            self.assertIn(texto, respuesta.content)

    def test_pdf_admite_multiples_articulos(self):
        producto_adicional = Producto.objects.create(
            empresa=self.empresa,
            familia=self.producto.familia,
            categoria=self.producto.categoria,
            tipo_item=Producto.TipoItem.SERVICIO,
            codigo_barra="SUC-002",
            nombre="Servicio adicional",
            precio=Decimal("75.50"),
        )
        DetallePedido.objects.create(
            pedido=self.pedido,
            producto=producto_adicional,
            cantidad=3,
        )

        self._pago_sucursal()
        respuesta = self.client.get(
            reverse("pedidos-pedidos-prefactura-pdf", args=[self.pedido.pk])
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertIn(b"SUC-001", respuesta.content)
        self.assertIn(b"SUC-002", respuesta.content)
        self.assertIn(b"Servicio adicional", respuesta.content)

    def test_pdf_varias_paginas_repite_tabla_y_conserva_totales(self):
        for indice in range(65):
            DetallePedido.objects.create(
                pedido=self.pedido,
                producto=self.producto,
                cantidad=1,
                codigo_articulo=f"LARGO-{indice:03d}",
                nombre_articulo=(
                    f"Articulo de prueba para validar paginacion {indice:03d}"
                ),
            )

        self._pago_sucursal()
        respuesta = self.client.get(
            reverse("pedidos-pedidos-prefactura-pdf", args=[self.pedido.pk])
        )

        paginas = re.findall(rb"/Type\s*/Page(?!s)", respuesta.content)
        self.assertGreater(len(paginas), 1)
        self.assertIn(b"LARGO-064", respuesta.content)
        self.assertIn(b"TOTAL", respuesta.content)

    def test_pdf_usa_logo_recortado_solo_como_identidad_visual(self):
        imagen = PILImage.new("RGB", (840, 670), "white")
        dibujo = ImageDraw.Draw(imagen)
        dibujo.polygon([(145, 420), (195, 295), (245, 420)], fill="#D1393D")
        dibujo.text((275, 320), "Empresa", fill="#2D4B77")
        contenido = BytesIO()
        imagen.save(contenido, format="PNG")

        with patch(
            "pedidos.prefacturas._contenido_logo_empresa",
            return_value=contenido.getvalue(),
        ):
            self._pago_sucursal()
            descarga = self.client.get(
                reverse("pedidos-pedidos-prefactura-pdf", args=[self.pedido.pk])
            )

        adjunto = mail.outbox[0].attachments[0].content
        self.assertIn(b"/Subtype /Image", descarga.content)
        self.assertEqual(adjunto, descarga.content)

    def test_reenvio_solo_al_comprador_y_con_limite(self):
        self._pago_sucursal()
        url = reverse(
            "pedidos-pedidos-reenviar-correo-prefactura",
            args=[self.pedido.pk],
        )
        primer_reenvio = self.client.post(url)
        segundo_reenvio = self.client.post(url)
        bloqueado = self.client.post(url)

        self.assertEqual(primer_reenvio.status_code, status.HTTP_200_OK)
        self.assertEqual(segundo_reenvio.status_code, status.HTTP_200_OK)
        self.assertEqual(bloqueado.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(len(mail.outbox), 3)
        self.assertTrue(
            all(mensaje.to == [self.comprador.email] for mensaje in mail.outbox)
        )
        self.assertEqual(Prefactura.objects.get(pedido=self.pedido).intentos_correo, 3)

    def test_confirmacion_administrativa_descuenta_una_sola_vez(self):
        creada = self._pago_sucursal()
        referencia = creada.data["pago"]["referencia"]
        self.client.force_authenticate(self.admin)
        url = reverse("pagos-confirmar-en-sucursal", args=[referencia])

        primera = self.client.post(url)
        segunda = self.client.post(url)

        self.assertEqual(primera.status_code, status.HTTP_200_OK)
        self.assertFalse(primera.data["duplicado"])
        self.assertEqual(segunda.status_code, status.HTTP_200_OK)
        self.assertTrue(segunda.data["duplicado"])
        self.pedido.refresh_from_db()
        self.producto.refresh_from_db()
        pago = Pago.objects.get(referencia=referencia)
        self.assertEqual(pago.estado, Pago.Estado.APROBADO)
        self.assertEqual(self.pedido.estado_pago, Pedido.EstadoPago.PAGADO)
        self.assertTrue(self.pedido.inventario_descontado)
        self.assertEqual(self.producto.existencia, 3)
        self.assertEqual(
            MovimientoInventario.objects.filter(referencia=self.pedido.numero).count(),
            1,
        )
        self.assertEqual(Prefactura.objects.filter(pedido=self.pedido).count(), 1)

    def test_comprador_no_puede_confirmar_y_admin_ajeno_no_ve_el_pago(self):
        creada = self._pago_sucursal()
        url = reverse(
            "pagos-confirmar-en-sucursal",
            args=[creada.data["pago"]["referencia"]],
        )
        comprador = self.client.post(url)
        self.client.force_authenticate(self.admin_otra)
        admin_ajeno = self.client.post(url)

        self.assertEqual(comprador.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(admin_ajeno.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(Pago.objects.get(pedido=self.pedido).estado, Pago.Estado.PENDIENTE)

    def test_inventario_insuficiente_revierte_confirmacion(self):
        creada = self._pago_sucursal()
        Producto.objects.filter(pk=self.producto.pk).update(existencia=1)
        self.client.force_authenticate(self.gerente)
        respuesta = self.client.post(
            reverse(
                "pagos-confirmar-en-sucursal",
                args=[creada.data["pago"]["referencia"]],
            )
        )

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.pedido.refresh_from_db()
        pago = Pago.objects.get(pedido=self.pedido)
        self.assertEqual(pago.estado, Pago.Estado.PENDIENTE)
        self.assertEqual(self.pedido.estado_pago, Pedido.EstadoPago.PENDIENTE)
        self.assertFalse(self.pedido.inventario_descontado)
        self.assertFalse(MovimientoInventario.objects.exists())

    def test_pago_en_linea_existente_conserva_su_flujo(self):
        self.empresa.pago_en_linea_activo = True
        self.empresa.pago_en_linea_proveedor = Empresa.ProveedorPagoEnLinea.SIMULADO
        self.empresa.save(
            update_fields=[
                "pago_en_linea_activo",
                "pago_en_linea_proveedor",
            ]
        )
        otro_pedido = self._crear_pedido(self.comprador)
        respuesta = self.client.post(
            reverse("pagos-iniciar"),
            {"pedido_id": otro_pedido.pk},
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        otro_pedido.refresh_from_db()
        pago = Pago.objects.get(pedido=otro_pedido)
        self.assertEqual(otro_pedido.metodo_pago, Pedido.MetodoPago.EN_LINEA)
        self.assertEqual(pago.metodo, Pago.Metodo.EN_LINEA)
        self.assertEqual(pago.proveedor, Empresa.ProveedorPagoEnLinea.SIMULADO)
        self.assertFalse(Prefactura.objects.filter(pedido=otro_pedido).exists())

    def test_admin_cancela_pedido_e_intento_pendiente_sin_tocar_inventario(self):
        creada = self._pago_sucursal()
        referencia = creada.data["pago"]["referencia"]
        self.client.force_authenticate(self.admin)

        respuesta = self.client.post(
            reverse(
                "pedidos-pedidos-cancelar-pendiente",
                args=[self.pedido.pk],
            ),
            {"motivo": "Pedido abandonado por el cliente"},
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertFalse(respuesta.data["duplicado"])
        self.assertEqual(respuesta.data["pedido"]["estado_pago"], "cancelado")
        self.assertEqual(respuesta.data["pedido"]["cancelado_por"], self.admin.pk)
        self.assertEqual(
            respuesta.data["pedido"]["motivo_cancelacion"],
            "Pedido abandonado por el cliente",
        )
        self.assertIsNotNone(respuesta.data["pedido"]["fecha_cancelacion"])
        self.assertEqual(len(respuesta.data["pagos_cancelados"]), 1)
        self.assertEqual(
            respuesta.data["pagos_cancelados"][0]["referencia"],
            referencia,
        )
        self.assertEqual(
            respuesta.data["pagos_cancelados"][0]["estado"],
            Pago.Estado.CANCELADO,
        )
        self.pedido.refresh_from_db()
        self.producto.refresh_from_db()
        self.assertFalse(self.pedido.inventario_descontado)
        self.assertEqual(self.producto.existencia, 5)
        self.assertFalse(MovimientoInventario.objects.exists())

    def test_cancelacion_pendiente_es_idempotente(self):
        self._pago_sucursal()
        self.client.force_authenticate(self.admin)
        url = reverse(
            "pedidos-pedidos-cancelar-pendiente",
            args=[self.pedido.pk],
        )

        primera = self.client.post(
            url,
            {"motivo": "Pedido abandonado"},
            format="json",
        )
        segunda = self.client.post(
            url,
            {"motivo": "Motivo diferente que no debe reemplazar el original"},
            format="json",
        )

        self.assertEqual(primera.status_code, status.HTTP_200_OK)
        self.assertEqual(segunda.status_code, status.HTTP_200_OK)
        self.assertFalse(primera.data["duplicado"])
        self.assertTrue(segunda.data["duplicado"])
        self.assertEqual(
            primera.data["pedido"]["fecha_cancelacion"],
            segunda.data["pedido"]["fecha_cancelacion"],
        )
        self.assertEqual(
            segunda.data["pedido"]["motivo_cancelacion"],
            "Pedido abandonado",
        )
        self.assertEqual(Pago.objects.filter(pedido=self.pedido).count(), 1)
        self.assertEqual(
            Pago.objects.get(pedido=self.pedido).estado,
            Pago.Estado.CANCELADO,
        )
        self.assertFalse(MovimientoInventario.objects.exists())

    def test_cancelacion_rechaza_comprador_y_administrador_de_otra_empresa(self):
        self._pago_sucursal()
        url = reverse(
            "pedidos-pedidos-cancelar-pendiente",
            args=[self.pedido.pk],
        )

        comprador = self.client.post(
            url,
            {"motivo": "Sin autorizacion"},
            format="json",
        )
        self.client.force_authenticate(self.admin_otra)
        administrador_ajeno = self.client.post(
            url,
            {"motivo": "Empresa incorrecta"},
            format="json",
        )

        self.assertEqual(comprador.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(administrador_ajeno.status_code, status.HTTP_403_FORBIDDEN)
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado_pago, Pedido.EstadoPago.PENDIENTE)
        self.assertEqual(
            Pago.objects.get(pedido=self.pedido).estado,
            Pago.Estado.PENDIENTE,
        )

    def test_cancelacion_rechaza_pedido_pagado_o_con_pago_aprobado(self):
        creada = self._pago_sucursal()
        referencia = creada.data["pago"]["referencia"]
        self.client.force_authenticate(self.admin)
        confirmada = self.client.post(
            reverse("pagos-confirmar-en-sucursal", args=[referencia])
        )
        self.assertEqual(confirmada.status_code, status.HTTP_200_OK)

        pedido_pagado = self.client.post(
            reverse(
                "pedidos-pedidos-cancelar-pendiente",
                args=[self.pedido.pk],
            ),
            {"motivo": "No debe cancelarse"},
            format="json",
        )

        otro_pedido = self._crear_pedido(self.otro_comprador)
        pago_aprobado = Pago.objects.create(
            pedido=otro_pedido,
            proveedor="prueba",
            metodo=Pago.Metodo.EN_LINEA,
        )
        Pago.objects.filter(pk=pago_aprobado.pk).update(
            estado=Pago.Estado.APROBADO,
        )
        inconsistente = self.client.post(
            reverse(
                "pedidos-pedidos-cancelar-pendiente",
                args=[otro_pedido.pk],
            ),
            {"motivo": "Tampoco debe cancelarse"},
            format="json",
        )

        self.assertEqual(pedido_pagado.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(inconsistente.status_code, status.HTTP_400_BAD_REQUEST)
        otro_pedido.refresh_from_db()
        self.assertEqual(otro_pedido.estado_pago, Pedido.EstadoPago.PENDIENTE)

    def test_cancelacion_solo_cambia_intentos_que_siguen_pendientes(self):
        self._pago_sucursal()
        rechazado = Pago.objects.get(pedido=self.pedido)
        Pago.objects.filter(pk=rechazado.pk).update(estado=Pago.Estado.RECHAZADO)
        self._pago_sucursal()
        pendiente = Pago.objects.get(
            pedido=self.pedido,
            estado=Pago.Estado.PENDIENTE,
        )
        self.client.force_authenticate(self.gerente)

        respuesta = self.client.post(
            reverse(
                "pedidos-pedidos-cancelar-pendiente",
                args=[self.pedido.pk],
            ),
            {"motivo": "Sin pago completado"},
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        rechazado.refresh_from_db()
        pendiente.refresh_from_db()
        self.assertEqual(rechazado.estado, Pago.Estado.RECHAZADO)
        self.assertEqual(pendiente.estado, Pago.Estado.CANCELADO)
        self.assertEqual(
            [item["id"] for item in respuesta.data["pagos_cancelados"]],
            [pendiente.id],
        )

    def test_cancelacion_pendiente_funciona_en_api_y_api_v1(self):
        pedido = self._crear_pedido(self.comprador)
        self.client.force_authenticate(self.admin)

        primera = self.client.post(
            f"/api/pedidos/pedidos/{pedido.pk}/cancelar-pendiente/",
            {"motivo": "Pedido abandonado"},
            format="json",
        )
        segunda = self.client.post(
            f"/api/v1/pedidos/pedidos/{pedido.pk}/cancelar-pendiente/",
            {"motivo": "Pedido abandonado"},
            format="json",
        )

        self.assertEqual(primera.status_code, status.HTTP_200_OK)
        self.assertEqual(segunda.status_code, status.HTTP_200_OK)
        self.assertFalse(primera.data["duplicado"])
        self.assertTrue(segunda.data["duplicado"])

    def test_rutas_api_y_api_v1_son_compatibles(self):
        pedido = self._crear_pedido(self.comprador)
        respuesta_api = self.client.post(
            f"/api/pedidos/pedidos/{pedido.pk}/pago-en-sucursal/",
            {"sucursal_id": self.sucursal.pk},
            format="json",
        )
        respuesta_v1 = self.client.post(
            f"/api/v1/pedidos/pedidos/{pedido.pk}/pago-en-sucursal/",
            {"sucursal_id": self.sucursal.pk},
            format="json",
        )

        self.assertEqual(respuesta_api.status_code, status.HTTP_201_CREATED)
        self.assertEqual(respuesta_v1.status_code, status.HTTP_200_OK)
        self.assertEqual(
            respuesta_api.data["prefactura"]["url_pdf"],
            f"/api/pedidos/pedidos/{pedido.pk}/prefactura/pdf/",
        )
        self.assertEqual(
            respuesta_v1.data["prefactura"]["url_pdf"],
            f"/api/v1/pedidos/pedidos/{pedido.pk}/prefactura/pdf/",
        )
        self.assertEqual(
            respuesta_api.data["pago"]["referencia"],
            respuesta_v1.data["pago"]["referencia"],
        )
        for base in ("/api", "/api/v1"):
            pdf = self.client.get(
                f"{base}/pedidos/pedidos/{pedido.pk}/prefactura/pdf/"
            )
            self.assertEqual(pdf.status_code, status.HTTP_200_OK)

        referencia = respuesta_api.data["pago"]["referencia"]
        self.client.force_authenticate(self.admin)
        confirmacion_api = self.client.post(
            f"/api/pagos/{referencia}/confirmar-en-sucursal/"
        )
        confirmacion_v1 = self.client.post(
            f"/api/v1/pagos/{referencia}/confirmar-en-sucursal/"
        )
        self.assertEqual(confirmacion_api.status_code, status.HTTP_200_OK)
        self.assertFalse(confirmacion_api.data["duplicado"])
        self.assertEqual(confirmacion_v1.status_code, status.HTTP_200_OK)
        self.assertTrue(confirmacion_v1.data["duplicado"])
