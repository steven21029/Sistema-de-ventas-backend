from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from catalogo.models import (
    Categoria,
    Familia,
    PaqueteCatalogo,
    PaqueteProducto,
    Producto,
)
from empresas.models import Empresa, Municipio
from inventario.models import MovimientoInventario
from promociones.models import DescuentoProducto, DescuentoPromocional
from usuarios.models import PerfilUsuario
from .models import Carrito, ItemCarrito, Pedido, TarifaEntrega


class CarritoServiciosTests(APITestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Analiza Servicios",
            slug="analiza-servicios",
            modo_inventario=Empresa.ModoInventario.SIN_INVENTARIO,
        )
        self.familia = Familia.objects.create(
            empresa=self.empresa,
            nombre="Examenes",
        )
        self.categoria = Categoria.objects.create(
            empresa=self.empresa,
            familia=self.familia,
            nombre="Laboratorio",
        )
        self.servicio = Producto.objects.create(
            empresa=self.empresa,
            familia=self.familia,
            categoria=self.categoria,
            nombre="Hemograma",
            precio="150.00",
        )
        self.usuario = get_user_model().objects.create_user(
            username="cliente-servicios@example.com",
            email="cliente-servicios@example.com",
            password="ClaveSegura123!",
        )
        self.usuario.perfil.empresa = self.empresa
        self.usuario.perfil.rol = PerfilUsuario.Rol.COMPRADOR
        self.usuario.perfil.activo = True
        self.usuario.perfil.correo_verificado = True
        self.usuario.perfil.save()
        self.client.force_authenticate(self.usuario)
        self.carrito = Carrito.objects.create(
            empresa=self.empresa,
            usuario=self.usuario,
        )

    def test_carrito_acepta_servicio_por_codigo_interno_sin_limite_stock(self):
        response = self.client.post(
            reverse(
                "pedidos-carritos-agregar-articulo",
                args=[self.carrito.pk],
            ),
            {
                "codigo": self.servicio.codigo_interno,
                "cantidad": 25,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["items"][0]["cantidad"], 25)
        self.assertFalse(response.data["items"][0]["controla_inventario"])
        self.assertNotIn("producto_nombre", response.data["items"][0])
        self.assertNotIn("imagen_principal", response.data["items"][0])

    def test_ruta_antigua_agregar_producto_ya_no_existe(self):
        response = self.client.post(
            f"/api/pedidos/carritos/{self.carrito.pk}/agregar-producto/",
            {
                "codigo": self.servicio.codigo_interno,
                "cantidad": 1,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_agregar_articulo_ya_no_acepta_codigo_barra_como_entrada(self):
        response = self.client.post(
            reverse(
                "pedidos-carritos-agregar-articulo",
                args=[self.carrito.pk],
            ),
            {
                "codigo_barra": "CODIGO-ANTIGUO-001",
                "cantidad": 1,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("codigo", response.data)

    def test_pedido_pagado_registra_venta_sin_movimiento_inventario(self):
        ItemCarrito.objects.create(
            carrito=self.carrito,
            producto=self.servicio,
            cantidad=3,
        )
        pedido = Pedido.generar_desde_carrito(
            carrito=self.carrito,
            tipo_entrega=Pedido.TipoEntrega.RETIRO_EN_LOCAL,
        )
        pedido.estado_pago = Pedido.EstadoPago.PAGADO
        pedido.save()
        pedido.refresh_from_db()

        detalle = pedido.detalles.get()
        self.assertEqual(detalle.codigo_interno, self.servicio.codigo_interno)
        self.assertIsNone(detalle.codigo_barra)
        self.assertTrue(pedido.inventario_descontado)
        self.assertFalse(
            MovimientoInventario.objects.filter(
                referencia=pedido.numero,
            ).exists()
        )

        response = self.client.get(
            reverse("catalogo-productos-mas-vendidos"),
            {"empresa_slug": self.empresa.slug},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["total_vendido"], 3)


class CalculoDescuentosCarritoTests(APITestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Ventas con Descuentos",
            slug="ventas-descuentos",
            modo_inventario=Empresa.ModoInventario.SIN_INVENTARIO,
        )
        familia = Familia.objects.create(
            empresa=self.empresa,
            nombre="Servicios",
        )
        categoria = Categoria.objects.create(
            empresa=self.empresa,
            familia=familia,
            nombre="Pruebas",
        )
        self.productos = [
            Producto.objects.create(
                empresa=self.empresa,
                familia=familia,
                categoria=categoria,
                nombre="Servicio 100",
                precio="100.00",
            ),
            Producto.objects.create(
                empresa=self.empresa,
                familia=familia,
                categoria=categoria,
                nombre="Servicio 200",
                precio="200.00",
            ),
            Producto.objects.create(
                empresa=self.empresa,
                familia=familia,
                categoria=categoria,
                nombre="Servicio 300",
                precio="300.00",
            ),
        ]
        DescuentoPromocional.objects.create(
            empresa=self.empresa,
            codigo="TODOS-10",
            titulo="Todos 10",
            alcance=DescuentoPromocional.Alcance.TODOS,
            porcentaje=10,
        )
        seleccionados = DescuentoPromocional.objects.create(
            empresa=self.empresa,
            codigo="SEL-15",
            titulo="Seleccionados 15",
            alcance=DescuentoPromocional.Alcance.SELECCIONADOS,
            porcentaje=15,
        )
        for producto in self.productos[:2]:
            DescuentoProducto.objects.create(
                descuento=seleccionados,
                producto=producto,
            )
        self.individual = DescuentoPromocional.objects.create(
            empresa=self.empresa,
            codigo="IND-20",
            titulo="Individual 20",
            alcance=DescuentoPromocional.Alcance.INDIVIDUAL,
            porcentaje=20,
        )
        DescuentoProducto.objects.create(
            descuento=self.individual,
            producto=self.productos[0],
        )

    def test_calculo_publico_aplica_un_solo_descuento_por_articulo(self):
        response = self.client.post(
            reverse("pedidos-carrito-calcular"),
            {
                "empresa_slug": self.empresa.slug,
                "items": [
                    {
                        "codigo": producto.codigo_interno,
                        "cantidad": 1,
                    }
                    for producto in self.productos
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [
                item["descuento_aplicado"]["porcentaje"]
                for item in response.data["items"]
            ],
            [20, 15, 10],
        )
        self.assertEqual(response.data["subtotal"], "600.00")
        self.assertEqual(response.data["descuento_total"], "80.00")
        self.assertEqual(response.data["base_imponible"], "520.00")
        self.assertEqual(response.data["impuesto"], "78.00")
        self.assertEqual(response.data["total_sin_envio"], "598.00")

    def test_pedido_guarda_fotografia_del_descuento(self):
        usuario = get_user_model().objects.create_user(
            username="cliente-descuentos@example.com",
            email="cliente-descuentos@example.com",
            password="ClaveSegura123!",
        )
        usuario.perfil.empresa = self.empresa
        usuario.perfil.rol = PerfilUsuario.Rol.COMPRADOR
        usuario.perfil.activo = True
        usuario.perfil.correo_verificado = True
        usuario.perfil.save()
        carrito = Carrito.objects.create(
            empresa=self.empresa,
            usuario=usuario,
        )
        ItemCarrito.objects.create(
            carrito=carrito,
            producto=self.productos[0],
            cantidad=2,
        )

        pedido = Pedido.generar_desde_carrito(
            carrito=carrito,
            tipo_entrega=Pedido.TipoEntrega.RETIRO_EN_LOCAL,
        )
        detalle = pedido.detalles.get()

        self.assertEqual(pedido.subtotal, 200)
        self.assertEqual(pedido.descuento_total, 40)
        self.assertEqual(pedido.impuesto, 24)
        self.assertEqual(pedido.total, 184)
        self.assertEqual(detalle.promocion_codigo, self.individual.codigo)
        self.assertEqual(detalle.promocion_titulo, self.individual.titulo)
        self.assertEqual(detalle.porcentaje_descuento, 20)
        self.assertEqual(detalle.descuento_unitario, 20)
        self.assertEqual(detalle.precio_unitario_final, 80)
        self.assertEqual(detalle.descuento_total, 40)
        self.assertEqual(detalle.subtotal_final, 160)

    def test_calculo_acepta_perfiles_y_combos_sin_descuento_promocional(self):
        perfil = PaqueteCatalogo.objects.create(
            empresa=self.empresa,
            tipo=PaqueteCatalogo.Tipo.PERFIL,
            codigo="PERFIL-001",
            nombre="Perfil independiente",
            precio_normal="500.00",
            precio_paquete="400.00",
        )
        combo = PaqueteCatalogo.objects.create(
            empresa=self.empresa,
            tipo=PaqueteCatalogo.Tipo.COMBO,
            codigo="COMBO-001",
            nombre="Combo independiente",
            precio_normal="450.00",
            precio_paquete="350.00",
        )
        PaqueteProducto.objects.create(
            paquete=perfil,
            producto=self.productos[0],
        )
        PaqueteProducto.objects.create(
            paquete=combo,
            producto=self.productos[1],
        )

        response = self.client.post(
            reverse("pedidos-carrito-calcular"),
            {
                "empresa_slug": self.empresa.slug,
                "items": [
                    {"codigo": perfil.codigo, "cantidad": 1},
                    {"codigo": combo.codigo, "cantidad": 1},
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["tipo_articulo"] for item in response.data["items"]],
            ["perfil", "combo"],
        )
        self.assertEqual(
            [item["precio_unitario"] for item in response.data["items"]],
            ["400.00", "350.00"],
        )
        self.assertEqual(
            [item["descuento_aplicado"] for item in response.data["items"]],
            [None, None],
        )
        self.assertEqual(response.data["subtotal"], "750.00")
        self.assertEqual(response.data["descuento_total"], "0.00")
        self.assertEqual(response.data["impuesto"], "112.50")
        self.assertEqual(response.data["total_sin_envio"], "862.50")

    def test_empresa_puede_desactivar_impuesto_en_calculo_publico(self):
        self.empresa.cobra_impuesto = False
        self.empresa.save(update_fields=["cobra_impuesto", "fecha_actualizacion"])

        response = self.client.post(
            reverse("pedidos-carrito-calcular"),
            {
                "empresa_slug": self.empresa.slug,
                "items": [
                    {
                        "codigo": self.productos[0].codigo_interno,
                        "cantidad": 1,
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["cobra_impuesto"])
        self.assertEqual(response.data["porcentaje_impuesto"], "0.00")
        self.assertEqual(response.data["base_imponible"], "80.00")
        self.assertEqual(response.data["impuesto"], "0.00")
        self.assertEqual(response.data["total_sin_envio"], "80.00")

    def test_pedido_conserva_decision_fiscal_de_la_empresa(self):
        self.empresa.cobra_impuesto = False
        self.empresa.save(update_fields=["cobra_impuesto", "fecha_actualizacion"])
        usuario = get_user_model().objects.create_user(
            username="cliente-sin-impuesto@example.com",
            email="cliente-sin-impuesto@example.com",
            password="ClaveSegura123!",
        )
        usuario.perfil.empresa = self.empresa
        usuario.perfil.rol = PerfilUsuario.Rol.COMPRADOR
        usuario.perfil.activo = True
        usuario.perfil.correo_verificado = True
        usuario.perfil.save()
        carrito = Carrito.objects.create(
            empresa=self.empresa,
            usuario=usuario,
        )
        ItemCarrito.objects.create(
            carrito=carrito,
            producto=self.productos[0],
            cantidad=1,
        )

        pedido = Pedido.generar_desde_carrito(
            carrito=carrito,
            tipo_entrega=Pedido.TipoEntrega.RETIRO_EN_LOCAL,
        )
        self.empresa.cobra_impuesto = True
        self.empresa.save(update_fields=["cobra_impuesto", "fecha_actualizacion"])
        pedido.estado_pago = Pedido.EstadoPago.PAGADO
        pedido.save()
        pedido.refresh_from_db()

        self.assertFalse(pedido.aplica_impuesto)
        self.assertEqual(pedido.tasa_impuesto, 0)
        self.assertEqual(pedido.impuesto, 0)
        self.assertEqual(pedido.total, 80)


class CarritoPaquetesPersistentesTests(APITestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Ventas mixtas persistentes",
            slug="ventas-mixtas-persistentes",
            modo_inventario=Empresa.ModoInventario.MIXTO,
        )
        self.familia = Familia.objects.create(
            empresa=self.empresa,
            nombre="Catalogo",
        )
        self.categoria = Categoria.objects.create(
            empresa=self.empresa,
            familia=self.familia,
            nombre="Articulos",
        )
        self.servicio = Producto.objects.create(
            empresa=self.empresa,
            familia=self.familia,
            categoria=self.categoria,
            tipo_item=Producto.TipoItem.SERVICIO,
            nombre="Consulta",
            precio="100.00",
        )
        self.fisico = Producto.objects.create(
            empresa=self.empresa,
            familia=self.familia,
            categoria=self.categoria,
            tipo_item=Producto.TipoItem.PRODUCTO_FISICO,
            codigo_barra="FISICO-001",
            nombre="Producto fisico",
            precio="50.00",
        )
        self.fisico_reemplazo = Producto.objects.create(
            empresa=self.empresa,
            familia=self.familia,
            categoria=self.categoria,
            tipo_item=Producto.TipoItem.PRODUCTO_FISICO,
            codigo_barra="FISICO-002",
            nombre="Producto reemplazo",
            precio="60.00",
        )
        Producto.objects.filter(
            pk__in=[self.fisico.pk, self.fisico_reemplazo.pk]
        ).update(existencia=5)
        self.fisico.refresh_from_db()
        self.fisico_reemplazo.refresh_from_db()
        self.perfil = PaqueteCatalogo.objects.create(
            empresa=self.empresa,
            tipo=PaqueteCatalogo.Tipo.PERFIL,
            codigo="PERFIL-PERSISTENTE",
            nombre="Perfil persistente",
            precio_normal="350.00",
            precio_paquete="300.00",
        )
        self.combo = PaqueteCatalogo.objects.create(
            empresa=self.empresa,
            tipo=PaqueteCatalogo.Tipo.COMBO,
            codigo="COMBO-PERSISTENTE",
            nombre="Combo persistente",
            precio_normal="250.00",
            precio_paquete="200.00",
        )
        PaqueteProducto.objects.create(
            paquete=self.perfil,
            producto=self.servicio,
        )
        PaqueteProducto.objects.create(
            paquete=self.combo,
            producto=self.fisico,
        )
        self.descuento = DescuentoPromocional.objects.create(
            empresa=self.empresa,
            codigo="CONSULTA-20",
            titulo="Consulta 20",
            alcance=DescuentoPromocional.Alcance.INDIVIDUAL,
            porcentaje=20,
        )
        DescuentoProducto.objects.create(
            descuento=self.descuento,
            producto=self.servicio,
        )
        self.usuario = get_user_model().objects.create_user(
            username="cliente-paquetes@example.com",
            email="cliente-paquetes@example.com",
            password="ClaveSegura123!",
        )
        self.usuario.perfil.empresa = self.empresa
        self.usuario.perfil.rol = PerfilUsuario.Rol.COMPRADOR
        self.usuario.perfil.activo = True
        self.usuario.perfil.correo_verificado = True
        self.usuario.perfil.save()
        self.client.force_authenticate(self.usuario)
        self.carrito = Carrito.objects.create(
            empresa=self.empresa,
            usuario=self.usuario,
        )

    def test_perfil_se_guarda_incrementa_y_recupera_del_carrito(self):
        url = reverse(
            "pedidos-carritos-agregar-articulo",
            args=[self.carrito.pk],
        )
        datos = {
            "codigo": self.perfil.codigo,
            "tipo_articulo": "perfil",
            "cantidad": 1,
        }

        primera = self.client.post(url, datos, format="json")
        segunda = self.client.post(url, datos, format="json")
        listado = self.client.get(
            reverse("pedidos-carritos-mi-carrito"),
        )

        self.assertEqual(primera.status_code, status.HTTP_200_OK)
        self.assertEqual(segunda.status_code, status.HTTP_200_OK)
        self.assertEqual(listado.status_code, status.HTTP_200_OK)
        self.assertEqual(ItemCarrito.objects.filter(carrito=self.carrito).count(), 1)
        self.assertEqual(listado.data["items"][0]["tipo_articulo"], "perfil")
        self.assertEqual(listado.data["items"][0]["codigo"], self.perfil.codigo)
        self.assertEqual(listado.data["items"][0]["cantidad"], 2)
        self.assertEqual(listado.data["items"][0]["precio_unitario"], "300.00")

    def test_mi_carrito_sincroniza_precio_actual_del_paquete(self):
        ItemCarrito.objects.create(
            carrito=self.carrito,
            paquete=self.perfil,
            cantidad=1,
        )
        self.perfil.precio_paquete = 275
        self.perfil.save(update_fields=["precio_paquete", "fecha_actualizacion"])

        response = self.client.get(
            reverse("pedidos-carritos-mi-carrito"),
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["items"][0]["precio_unitario"], "275.00")
        self.assertEqual(response.data["subtotal"], "275.00")

    def test_endpoint_directo_no_escribe_en_carrito_de_otro_usuario(self):
        otro_usuario = get_user_model().objects.create_user(
            username="otro-cliente-paquetes@example.com",
            email="otro-cliente-paquetes@example.com",
            password="ClaveSegura123!",
        )
        otro_usuario.perfil.empresa = self.empresa
        otro_usuario.perfil.rol = PerfilUsuario.Rol.COMPRADOR
        otro_usuario.perfil.activo = True
        otro_usuario.perfil.correo_verificado = True
        otro_usuario.perfil.save()
        otro_carrito = Carrito.objects.create(
            empresa=self.empresa,
            usuario=otro_usuario,
        )

        crear = self.client.post(
            reverse("pedidos-items-carrito-list"),
            {
                "carrito": otro_carrito.pk,
                "producto": self.servicio.pk,
                "cantidad": 1,
            },
            format="json",
        )
        self.assertEqual(crear.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(ItemCarrito.objects.filter(carrito=otro_carrito).exists())

        item_propio = ItemCarrito.objects.create(
            carrito=self.carrito,
            producto=self.servicio,
            cantidad=1,
        )
        mover = self.client.patch(
            reverse("pedidos-items-carrito-detail", args=[item_propio.pk]),
            {"carrito": otro_carrito.pk},
            format="json",
        )
        self.assertEqual(mover.status_code, status.HTTP_403_FORBIDDEN)
        item_propio.refresh_from_db()
        self.assertEqual(item_propio.carrito, self.carrito)

    def test_inventario_se_valida_sumando_paquetes_compartidos(self):
        otro_paquete = PaqueteCatalogo.objects.create(
            empresa=self.empresa,
            tipo=PaqueteCatalogo.Tipo.PERFIL,
            codigo="PERFIL-FISICO",
            nombre="Perfil con fisico",
            precio_normal="150.00",
            precio_paquete="120.00",
        )
        PaqueteProducto.objects.create(
            paquete=otro_paquete,
            producto=self.fisico,
        )
        url = reverse(
            "pedidos-carritos-agregar-articulo",
            args=[self.carrito.pk],
        )
        primera = self.client.post(
            url,
            {
                "codigo": self.combo.codigo,
                "tipo_articulo": "combo",
                "cantidad": 3,
            },
            format="json",
        )
        segunda = self.client.post(
            url,
            {
                "codigo": otro_paquete.codigo,
                "tipo_articulo": "perfil",
                "cantidad": 3,
            },
            format="json",
        )

        self.assertEqual(primera.status_code, status.HTTP_200_OK)
        self.assertEqual(segunda.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ItemCarrito.objects.filter(carrito=self.carrito).count(), 1)

    def test_calculador_publico_suma_inventario_entre_paquetes(self):
        otro_paquete = PaqueteCatalogo.objects.create(
            empresa=self.empresa,
            tipo=PaqueteCatalogo.Tipo.PERFIL,
            codigo="PERFIL-CALCULO-FISICO",
            nombre="Perfil calculo fisico",
            precio_normal="150.00",
            precio_paquete="120.00",
        )
        PaqueteProducto.objects.create(
            paquete=otro_paquete,
            producto=self.fisico,
        )

        response = self.client.post(
            reverse("pedidos-carrito-calcular"),
            {
                "empresa_slug": self.empresa.slug,
                "items": [
                    {
                        "codigo": self.combo.codigo,
                        "tipo_articulo": "combo",
                        "cantidad": 3,
                    },
                    {
                        "codigo": otro_paquete.codigo,
                        "tipo_articulo": "perfil",
                        "cantidad": 3,
                    },
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("items", response.data)

    def test_calculador_publico_rechaza_componentes_inactivos(self):
        self.fisico.activo = False
        self.fisico.save(update_fields=["activo", "fecha_actualizacion"])

        response = self.client.post(
            reverse("pedidos-carrito-calcular"),
            {
                "empresa_slug": self.empresa.slug,
                "items": [
                    {
                        "codigo": self.combo.codigo,
                        "tipo_articulo": "combo",
                        "cantidad": 1,
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("items", response.data)

    def test_pedido_conserva_componentes_y_descuenta_fotografia_comprada(self):
        ItemCarrito.objects.create(
            carrito=self.carrito,
            producto=self.servicio,
            cantidad=1,
        )
        ItemCarrito.objects.create(
            carrito=self.carrito,
            paquete=self.perfil,
            cantidad=1,
        )
        ItemCarrito.objects.create(
            carrito=self.carrito,
            paquete=self.combo,
            cantidad=2,
        )

        pedido = Pedido.generar_desde_carrito(
            carrito=self.carrito,
            tipo_entrega=Pedido.TipoEntrega.RETIRO_EN_LOCAL,
        )
        detalles = {
            detalle.tipo_articulo: detalle
            for detalle in pedido.detalles.prefetch_related("componentes")
        }

        self.assertEqual(pedido.subtotal, 800)
        self.assertEqual(pedido.descuento_total, 20)
        self.assertEqual(pedido.impuesto, 117)
        self.assertEqual(pedido.total, 897)
        self.assertEqual(detalles["producto"].porcentaje_descuento, 20)
        self.assertEqual(detalles["perfil"].porcentaje_descuento, 0)
        self.assertEqual(detalles["combo"].porcentaje_descuento, 0)
        self.assertEqual(detalles["perfil"].codigo_articulo, self.perfil.codigo)
        self.assertEqual(detalles["combo"].nombre_articulo, self.combo.nombre)
        self.assertEqual(
            detalles["combo"].componentes.get().producto,
            self.fisico,
        )
        componente_fotografiado = detalles["combo"].componentes.get()
        componente_fotografiado.nombre_producto = "Componente alterado"
        with self.assertRaises(ValidationError):
            componente_fotografiado.save()

        response = self.client.get(
            reverse("pedidos-pedidos-detail", args=[pedido.pk]),
        )
        detalle_combo = next(
            detalle
            for detalle in response.data["detalles"]
            if detalle["tipo_articulo"] == "combo"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("producto_nombre_actual", detalle_combo)
        self.assertNotIn("articulo_nombre_actual", detalle_combo)
        self.assertEqual(detalle_combo["codigo_articulo"], self.combo.codigo)
        self.assertEqual(
            detalle_combo["componentes"][0]["codigo_barra"],
            self.fisico.codigo_barra,
        )

        PaqueteProducto.objects.filter(paquete=self.combo).delete()
        PaqueteProducto.objects.create(
            paquete=self.combo,
            producto=self.fisico_reemplazo,
        )
        pedido.estado_pago = Pedido.EstadoPago.PAGADO
        pedido.save()
        self.fisico.refresh_from_db()
        self.fisico_reemplazo.refresh_from_db()

        self.assertEqual(self.fisico.existencia, 3)
        self.assertEqual(self.fisico_reemplazo.existencia, 5)
        movimiento = MovimientoInventario.objects.get(
            referencia=pedido.numero,
            producto=self.fisico,
        )
        self.assertEqual(movimiento.cantidad, 2)

    def test_pago_conserva_tarifa_y_nombre_fotografiados(self):
        self.empresa.tiene_envios = True
        self.empresa.save(update_fields=["tiene_envios", "fecha_actualizacion"])
        tarifa = TarifaEntrega.objects.create(
            empresa=self.empresa,
            tipo_entrega=Pedido.TipoEntrega.ENVIO_LOCAL,
            monto="25.00",
        )
        ItemCarrito.objects.create(
            carrito=self.carrito,
            producto=self.servicio,
            cantidad=1,
        )
        nombre_comprado = self.servicio.nombre
        pedido = Pedido.generar_desde_carrito(
            carrito=self.carrito,
            tipo_entrega=Pedido.TipoEntrega.ENVIO_LOCAL,
            datos_entrega={
                "nombre_recibe": "Cliente original",
                "telefono_recibe": "99999999",
                "direccion_entrega": "Direccion original",
                "departamento_entrega": "Francisco Morazan",
                "municipio_entrega": "Tegucigalpa",
            },
        )
        envio_comprado = pedido.envio
        total_comprado = pedido.total

        tarifa.monto = "90.00"
        tarifa.save(update_fields=["monto", "fecha_actualizacion"])
        self.servicio.nombre = "Consulta renombrada"
        self.servicio.precio = "999.00"
        self.servicio.save()
        self.empresa.tiene_envios = False
        self.empresa.save(update_fields=["tiene_envios", "fecha_actualizacion"])

        pedido.estado_pago = Pedido.EstadoPago.PAGADO
        pedido.full_clean()
        pedido.save()
        pedido.refresh_from_db()
        detalle = pedido.detalles.get()

        self.assertEqual(pedido.envio, envio_comprado)
        self.assertEqual(pedido.total, total_comprado)
        self.assertEqual(detalle.nombre_articulo, nombre_comprado)
        self.assertEqual(detalle.precio_unitario, 100)

        pedido.estado_pago = Pedido.EstadoPago.PENDIENTE
        with self.assertRaises(ValidationError):
            pedido.save()

    def test_pedido_conserva_municipio_de_entrega_catalogado(self):
        self.empresa.tiene_envios = True
        self.empresa.save(update_fields=["tiene_envios", "fecha_actualizacion"])
        TarifaEntrega.objects.create(
            empresa=self.empresa,
            tipo_entrega=Pedido.TipoEntrega.ENVIO_LOCAL,
            monto="25.00",
        )
        municipio = Municipio.objects.select_related("departamento").get(codigo="0801")
        ItemCarrito.objects.create(
            carrito=self.carrito,
            producto=self.servicio,
            cantidad=1,
        )

        pedido = Pedido.generar_desde_carrito(
            carrito=self.carrito,
            tipo_entrega=Pedido.TipoEntrega.ENVIO_LOCAL,
            datos_entrega={
                "nombre_recibe": "Cliente",
                "telefono_recibe": "99999999",
                "direccion_entrega": "Direccion",
                "municipio_entrega_catalogo": municipio,
            },
        )

        self.assertEqual(pedido.municipio_entrega_catalogo_id, municipio.pk)
        self.assertEqual(pedido.municipio_entrega, "Distrito Central")
        self.assertEqual(pedido.departamento_entrega, "Francisco Morazan")

    def test_fotografia_no_se_puede_editar_ni_eliminar(self):
        ItemCarrito.objects.create(
            carrito=self.carrito,
            producto=self.servicio,
            cantidad=1,
        )
        pedido = Pedido.generar_desde_carrito(
            carrito=self.carrito,
            tipo_entrega=Pedido.TipoEntrega.RETIRO_EN_LOCAL,
        )
        detalle = pedido.detalles.get()

        pedido.subtotal = 1
        with self.assertRaises(ValidationError):
            pedido.save()

        detalle.nombre_articulo = "Nombre alterado"
        with self.assertRaises(ValidationError):
            detalle.save()

        with self.assertRaises(ValidationError):
            pedido.delete()

    def test_api_de_pedidos_y_detalles_es_solo_lectura(self):
        ItemCarrito.objects.create(
            carrito=self.carrito,
            producto=self.servicio,
            cantidad=1,
        )
        pedido = Pedido.generar_desde_carrito(
            carrito=self.carrito,
            tipo_entrega=Pedido.TipoEntrega.RETIRO_EN_LOCAL,
        )
        detalle = pedido.detalles.get()

        editar_pedido = self.client.patch(
            reverse("pedidos-pedidos-detail", args=[pedido.pk]),
            {"subtotal": "1.00"},
            format="json",
        )
        editar_detalle = self.client.patch(
            reverse("pedidos-detalles-detail", args=[detalle.pk]),
            {"cantidad": 99},
            format="json",
        )
        eliminar_pedido = self.client.delete(
            reverse("pedidos-pedidos-detail", args=[pedido.pk]),
        )

        self.assertEqual(editar_pedido.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(editar_detalle.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(eliminar_pedido.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
