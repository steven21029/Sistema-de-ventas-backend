from datetime import UTC, datetime
from decimal import Decimal
from io import BytesIO
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.urls import reverse
from openpyxl import load_workbook
from rest_framework import status
from rest_framework.test import APITestCase

from catalogo.models import Categoria, Familia, Producto
from empresas.models import Empresa
from pagos.models import Pago
from pedidos.models import DetallePedido, Pedido
from usuarios.models import PerfilUsuario


User = get_user_model()
ZONA_HONDURAS = ZoneInfo("America/Tegucigalpa")


class ReportesVentasAPITests(APITestCase):
    def setUp(self):
        self.analiza = Empresa.objects.create(
            nombre="Analiza",
            slug="analiza",
            modo_inventario=Empresa.ModoInventario.SIN_INVENTARIO,
            cobra_impuesto=True,
        )
        self.otra = Empresa.objects.create(
            nombre="Otra empresa",
            slug="otra",
            modo_inventario=Empresa.ModoInventario.SIN_INVENTARIO,
            cobra_impuesto=True,
        )
        self.admin = self._crear_usuario(
            "admin",
            PerfilUsuario.Rol.ADMINISTRADOR_EMPRESA,
            self.analiza,
        )
        self.gerente = self._crear_usuario(
            "gerente",
            PerfilUsuario.Rol.GERENTE,
            self.analiza,
        )
        self.comprador = self._crear_usuario(
            "comprador",
            PerfilUsuario.Rol.COMPRADOR,
            self.analiza,
        )
        self.comprador_otra = self._crear_usuario(
            "comprador-otra",
            PerfilUsuario.Rol.COMPRADOR,
            self.otra,
        )
        self.admin_otra = self._crear_usuario(
            "admin-otra",
            PerfilUsuario.Rol.ADMINISTRADOR_EMPRESA,
            self.otra,
        )
        self.maestro = self._crear_usuario(
            "maestro",
            PerfilUsuario.Rol.ADMINISTRADOR_MAESTRO,
            None,
        )
        self.maestro.perfil.empresas_permitidas.add(self.analiza)
        self.superusuario = User.objects.create_superuser(
            username="root",
            email="root@example.com",
            password="Prueba12345!",
        )

        familia = Familia.objects.create(empresa=self.analiza, nombre="Examenes")
        categoria = Categoria.objects.create(
            empresa=self.analiza,
            familia=familia,
            nombre="Laboratorio",
        )
        self.hemograma = Producto.objects.create(
            empresa=self.analiza,
            familia=familia,
            categoria=categoria,
            codigo_barra="EXA-001",
            nombre="Hemograma",
            precio=Decimal("50.00"),
        )

        self.pagado = self._crear_pedido(
            self.analiza,
            self.comprador,
            datetime(2026, 8, 5, 10, 0, tzinfo=ZONA_HONDURAS),
            estado=Pedido.EstadoPago.PAGADO,
            subtotal="100.00",
            descuentos="10.00",
            impuestos="13.50",
            envios="20.00",
            total="123.50",
        )
        DetallePedido.objects.create(
            pedido=self.pagado,
            producto=self.hemograma,
            precio_unitario=Decimal("50.00"),
            cantidad=2,
            porcentaje_descuento=10,
        )

        self.aprobado_por_pago = self._crear_pedido(
            self.analiza,
            self.comprador,
            datetime(2026, 8, 6, 11, 0, tzinfo=ZONA_HONDURAS),
            subtotal="50.00",
            impuestos="7.50",
            total="57.50",
        )
        pago_aprobado = Pago.objects.create(
            pedido=self.aprobado_por_pago,
            proveedor="prueba",
        )
        Pago.objects.filter(pk=pago_aprobado.pk).update(
            estado=Pago.Estado.APROBADO,
            fecha_confirmacion=self._utc(2026, 8, 6, 11, 5),
            fecha_creacion=self._utc(2026, 8, 6, 11, 1),
        )

        self.pendiente = self._crear_pedido(
            self.analiza,
            self.comprador,
            datetime(2026, 8, 7, 12, 0, tzinfo=ZONA_HONDURAS),
            subtotal="40.00",
            impuestos="6.00",
            total="46.00",
        )
        self.rechazado = self._crear_pedido(
            self.analiza,
            self.comprador,
            datetime(2026, 8, 8, 13, 0, tzinfo=ZONA_HONDURAS),
            subtotal="30.00",
            impuestos="4.50",
            total="34.50",
        )
        pago_rechazado = Pago.objects.create(
            pedido=self.rechazado,
            proveedor="prueba",
        )
        Pago.objects.filter(pk=pago_rechazado.pk).update(
            estado=Pago.Estado.RECHAZADO,
            fecha_confirmacion=self._utc(2026, 8, 8, 13, 5),
            fecha_creacion=self._utc(2026, 8, 8, 13, 1),
        )
        self.cancelado = self._crear_pedido(
            self.analiza,
            self.comprador,
            datetime(2026, 8, 9, 14, 0, tzinfo=ZONA_HONDURAS),
            estado=Pedido.EstadoPago.CANCELADO,
            subtotal="20.00",
            impuestos="3.00",
            total="23.00",
        )
        self.anterior = self._crear_pedido(
            self.analiza,
            self.comprador,
            datetime(2026, 7, 10, 10, 0, tzinfo=ZONA_HONDURAS),
            estado=Pedido.EstadoPago.PAGADO,
            subtotal="80.00",
            impuestos="12.00",
            total="92.00",
        )
        self.fuera_rango = self._crear_pedido(
            self.analiza,
            self.comprador,
            datetime(2026, 9, 1, 0, 1, tzinfo=ZONA_HONDURAS),
            estado=Pedido.EstadoPago.PAGADO,
            subtotal="200.00",
            impuestos="30.00",
            total="230.00",
        )
        self.pedido_otra = self._crear_pedido(
            self.otra,
            self.comprador_otra,
            datetime(2026, 8, 5, 10, 0, tzinfo=ZONA_HONDURAS),
            estado=Pedido.EstadoPago.PAGADO,
            subtotal="999.00",
            impuestos="149.85",
            total="1148.85",
        )

    def _crear_usuario(self, username, rol, empresa):
        usuario = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="Prueba12345!",
        )
        perfil = usuario.perfil
        perfil.rol = rol
        perfil.empresa = empresa
        perfil.correo_verificado = True
        perfil.activo = True
        perfil.save()
        return usuario

    def _crear_pedido(
        self,
        empresa,
        usuario,
        fecha,
        estado=Pedido.EstadoPago.PENDIENTE,
        subtotal="100.00",
        descuentos="0.00",
        impuestos="15.00",
        envios="0.00",
        total="115.00",
    ):
        pedido = Pedido.objects.create(
            empresa=empresa,
            usuario=usuario,
            tipo_entrega=Pedido.TipoEntrega.RETIRO_EN_LOCAL,
            subtotal=Decimal(subtotal),
            descuento_total=Decimal(descuentos),
        )
        Pedido.objects.filter(pk=pedido.pk).update(
            estado_pago=estado,
            subtotal=Decimal(subtotal),
            descuento_total=Decimal(descuentos),
            impuesto=Decimal(impuestos),
            envio=Decimal(envios),
            total=Decimal(total),
            fecha_creacion=fecha.astimezone(UTC),
        )
        return Pedido.objects.get(pk=pedido.pk)

    def _utc(self, year, month, day, hour, minute):
        return datetime(
            year,
            month,
            day,
            hour,
            minute,
            tzinfo=ZONA_HONDURAS,
        ).astimezone(UTC)

    def _parametros_resumen(self, **extra):
        parametros = {
            "empresa_slug": self.analiza.slug,
            "fecha_desde": "2026-08-01",
            "fecha_hasta": "2026-08-31",
            "agrupacion": "mes",
            "comparar_periodo_anterior": "true",
        }
        parametros.update(extra)
        return parametros

    def _parametros_exportacion(self, formato, tipo):
        return {
            "empresa_slug": self.analiza.slug,
            "fecha_desde": "2026-08-01",
            "fecha_hasta": "2026-08-31",
            "formato": formato,
            "tipo": tipo,
        }

    def test_resumen_usa_solo_ventas_confirmadas_y_totales_historicos(self):
        self.client.force_authenticate(self.admin)
        respuesta = self.client.get(
            reverse("reportes-resumen-ventas"),
            self._parametros_resumen(),
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        resumen = respuesta.data["resumen"]
        self.assertEqual(respuesta.data["empresa_slug"], "analiza")
        self.assertEqual(respuesta.data["moneda"], "HNL")
        self.assertEqual(resumen["ingresos_confirmados"], "181.00")
        self.assertEqual(resumen["ventas_confirmadas"], 2)
        self.assertEqual(resumen["ticket_promedio"], "90.50")
        self.assertEqual(resumen["subtotal"], "150.00")
        self.assertEqual(resumen["descuentos"], "10.00")
        self.assertEqual(resumen["impuestos"], "21.00")
        self.assertEqual(resumen["envios"], "20.00")
        self.assertEqual(resumen["monto_pendiente"], "46.00")
        self.assertEqual(resumen["pedidos_pendientes"], 1)

    def test_desglosa_pagados_pendientes_rechazados_y_cancelados(self):
        self.client.force_authenticate(self.admin)
        respuesta = self.client.get(
            reverse("reportes-resumen-ventas"),
            self._parametros_resumen(),
        )

        estados = {item["estado"]: item for item in respuesta.data["estados"]}
        self.assertEqual(estados["pagado"], {"estado": "pagado", "cantidad": 2, "monto": "181.00"})
        self.assertEqual(estados["pendiente"]["cantidad"], 1)
        self.assertEqual(estados["rechazado"]["cantidad"], 1)
        self.assertEqual(estados["cancelado"]["cantidad"], 1)

    def test_comparacion_mensual_y_producto_mas_vendido(self):
        self.client.force_authenticate(self.admin)
        respuesta = self.client.get(
            reverse("reportes-resumen-ventas"),
            self._parametros_resumen(),
        )

        self.assertEqual(
            respuesta.data["resumen"]["variacion_ingresos_porcentaje"],
            96.7,
        )
        self.assertEqual(
            respuesta.data["resumen"]["variacion_ventas_porcentaje"],
            100.0,
        )
        self.assertEqual(
            respuesta.data["serie"],
            [{"periodo": "2026-08", "etiqueta": "Ago", "ingresos": "181.00", "ventas": 2}],
        )
        self.assertEqual(
            respuesta.data["productos_mas_vendidos"][0],
            {
                "codigo": "EXA-001",
                "nombre": "Hemograma",
                "cantidad": 2,
                "ingresos": "90.00",
            },
        )

    def test_rango_fechas_es_inclusivo_y_respeta_hora_honduras(self):
        self.client.force_authenticate(self.admin)
        respuesta = self.client.get(
            reverse("reportes-resumen-ventas"),
            self._parametros_resumen(
                fecha_desde="2026-08-05",
                fecha_hasta="2026-08-05",
                agrupacion="dia",
                comparar_periodo_anterior="false",
            ),
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta.data["resumen"]["ventas_confirmadas"], 1)
        self.assertEqual(respuesta.data["resumen"]["ingresos_confirmados"], "123.50")
        self.assertEqual(respuesta.data["serie"][0]["periodo"], "2026-08-05")

    def test_rechaza_rango_invertido(self):
        self.client.force_authenticate(self.admin)
        respuesta = self.client.get(
            reverse("reportes-resumen-ventas"),
            self._parametros_resumen(
                fecha_desde="2026-08-31",
                fecha_hasta="2026-08-01",
            ),
        )

        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("fecha_hasta", respuesta.data)

    def test_aislamiento_multiempresa(self):
        self.client.force_authenticate(self.admin)
        propia = self.client.get(
            reverse("reportes-resumen-ventas"),
            self._parametros_resumen(),
        )
        ajena = self.client.get(
            reverse("reportes-resumen-ventas"),
            self._parametros_resumen(empresa_slug=self.otra.slug),
        )

        self.assertEqual(propia.status_code, status.HTTP_200_OK)
        self.assertNotEqual(
            propia.data["resumen"]["ingresos_confirmados"],
            "1148.85",
        )
        self.assertEqual(ajena.status_code, status.HTTP_403_FORBIDDEN)

    def test_permisos_por_rol(self):
        url = reverse("reportes-resumen-ventas")
        for usuario in (self.superusuario, self.admin, self.gerente, self.maestro):
            self.client.force_authenticate(usuario)
            respuesta = self.client.get(url, self._parametros_resumen())
            self.assertEqual(respuesta.status_code, status.HTTP_200_OK)

        for usuario in (self.comprador, self.admin_otra):
            self.client.force_authenticate(usuario)
            respuesta = self.client.get(url, self._parametros_resumen())
            self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.comprador)
        exportacion = self.client.get(
            reverse("reportes-ventas-exportar"),
            self._parametros_exportacion("csv", "resumen"),
        )
        self.assertEqual(exportacion.status_code, status.HTTP_403_FORBIDDEN)

    def test_maestro_no_accede_empresa_no_asignada(self):
        self.client.force_authenticate(self.maestro)
        respuesta = self.client.get(
            reverse("reportes-resumen-ventas"),
            self._parametros_resumen(empresa_slug=self.otra.slug),
        )
        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

    def test_rutas_api_y_api_v1_son_compatibles(self):
        self.client.force_authenticate(self.admin)
        for ruta in (
            "/api/reportes/resumen-ventas/",
            "/api/v1/reportes/resumen-ventas/",
        ):
            respuesta = self.client.get(ruta, self._parametros_resumen())
            self.assertEqual(respuesta.status_code, status.HTTP_200_OK)

        for ruta in (
            "/api/reportes/ventas/exportar/",
            "/api/v1/reportes/ventas/exportar/",
        ):
            respuesta = self.client.get(
                ruta,
                self._parametros_exportacion("csv", "resumen"),
            )
            self.assertEqual(respuesta.status_code, status.HTTP_200_OK)

    def test_exportacion_csv(self):
        self.client.force_authenticate(self.admin)
        respuesta = self.client.get(
            reverse("reportes-ventas-exportar"),
            self._parametros_exportacion("csv", "ventas"),
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertTrue(respuesta["Content-Type"].startswith("text/csv"))
        self.assertIn(".csv", respuesta["Content-Disposition"])
        contenido = respuesta.content.decode("utf-8-sig")
        self.assertIn("Analiza", contenido)
        self.assertIn(self.pagado.numero, contenido)
        self.assertNotIn(self.pedido_otra.numero, contenido)

    def test_exportacion_xlsx(self):
        self.client.force_authenticate(self.admin)
        respuesta = self.client.get(
            reverse("reportes-ventas-exportar"),
            self._parametros_exportacion("xlsx", "pagos"),
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(
            respuesta["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        libro = load_workbook(BytesIO(respuesta.content), read_only=True)
        valores = [
            str(celda)
            for fila in libro.active.iter_rows(values_only=True)
            for celda in fila
            if celda is not None
        ]
        self.assertIn("Analiza", valores)
        self.assertIn("Detalle de pagos", valores)

    def test_exportacion_pdf(self):
        self.client.force_authenticate(self.admin)
        respuesta = self.client.get(
            reverse("reportes-ventas-exportar"),
            self._parametros_exportacion("pdf", "impuestos"),
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertEqual(respuesta["Content-Type"], "application/pdf")
        self.assertIn(".pdf", respuesta["Content-Disposition"])
        self.assertTrue(respuesta.content.startswith(b"%PDF"))
