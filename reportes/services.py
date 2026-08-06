import csv
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from html import escape
from io import BytesIO, StringIO
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db.models import Count, Exists, OuterRef, Q, Sum
from django.utils import timezone

from pagos.models import Pago
from pedidos.models import DetallePedido, Pedido


ZERO = Decimal("0.00")
MONEY_QUANTIZER = Decimal("0.01")
PERCENT_QUANTIZER = Decimal("0.1")
MESES = (
    "",
    "Ene",
    "Feb",
    "Mar",
    "Abr",
    "May",
    "Jun",
    "Jul",
    "Ago",
    "Sep",
    "Oct",
    "Nov",
    "Dic",
)
ORDEN_ESTADOS = ("pagado", "pendiente", "rechazado", "cancelado")


def formatear_monto(valor):
    return str((valor or ZERO).quantize(MONEY_QUANTIZER, rounding=ROUND_HALF_UP))


def _limpiar_celda(valor):
    if valor is None:
        return ""
    texto = str(valor)
    if texto.startswith(("=", "+", "-", "@")):
        return f"'{texto}"
    return texto


@dataclass(frozen=True)
class ReporteTabular:
    titulo: str
    metadata: tuple
    totales: tuple
    encabezados: tuple
    filas: tuple


class ReporteVentasService:
    def __init__(self, empresa, fecha_desde, fecha_hasta, agrupacion="dia"):
        self.empresa = empresa
        self.fecha_desde = fecha_desde
        self.fecha_hasta = fecha_hasta
        self.agrupacion = agrupacion
        self.zona_horaria = ZoneInfo(settings.TIME_ZONE)
        self.inicio, self.fin_exclusivo = self._limites(
            fecha_desde,
            fecha_hasta,
        )

    def construir_resumen(self, comparar_periodo_anterior=False):
        pedidos = self._pedidos_periodo(self.fecha_desde, self.fecha_hasta)
        confirmados = self._pedidos_confirmados(pedidos)
        totales = self._totales_confirmados(confirmados)
        estados, acumulados_estados = self._estados(pedidos)

        variacion_ingresos = None
        variacion_ventas = None
        if comparar_periodo_anterior:
            dias_periodo = (self.fecha_hasta - self.fecha_desde).days + 1
            anterior_hasta = self.fecha_desde - timedelta(days=1)
            anterior_desde = anterior_hasta - timedelta(days=dias_periodo - 1)
            anteriores = self._pedidos_confirmados(
                self._pedidos_periodo(anterior_desde, anterior_hasta)
            )
            totales_anteriores = self._totales_confirmados(anteriores)
            variacion_ingresos = self._variacion(
                totales["ingresos"],
                totales_anteriores["ingresos"],
            )
            variacion_ventas = self._variacion(
                Decimal(totales["ventas"]),
                Decimal(totales_anteriores["ventas"]),
            )

        return {
            "empresa_slug": self.empresa.slug,
            "moneda": self._moneda(pedidos),
            "periodo": {
                "fecha_desde": self.fecha_desde.isoformat(),
                "fecha_hasta": self.fecha_hasta.isoformat(),
            },
            "resumen": {
                "ingresos_confirmados": formatear_monto(totales["ingresos"]),
                "ventas_confirmadas": totales["ventas"],
                "ticket_promedio": formatear_monto(totales["ticket_promedio"]),
                "subtotal": formatear_monto(totales["subtotal"]),
                "descuentos": formatear_monto(totales["descuentos"]),
                "impuestos": formatear_monto(totales["impuestos"]),
                "envios": formatear_monto(totales["envios"]),
                "monto_pendiente": formatear_monto(
                    acumulados_estados["pendiente"]["monto"]
                ),
                "pedidos_pendientes": acumulados_estados["pendiente"]["cantidad"],
                "variacion_ingresos_porcentaje": variacion_ingresos,
                "variacion_ventas_porcentaje": variacion_ventas,
            },
            "serie": self._serie(confirmados),
            "estados": estados,
            "productos_mas_vendidos": self._productos_mas_vendidos(confirmados),
        }

    def construir_tabla(self, tipo):
        resumen = self.construir_resumen(comparar_periodo_anterior=False)
        metadata = (
            ("Empresa", self.empresa.nombre),
            ("Empresa slug", self.empresa.slug),
            (
                "Periodo",
                f"{self.fecha_desde.isoformat()} a {self.fecha_hasta.isoformat()}",
            ),
            ("Moneda", resumen["moneda"]),
        )
        resumen_totales = resumen["resumen"]
        totales = (
            ("Ingresos confirmados", resumen_totales["ingresos_confirmados"]),
            ("Ventas confirmadas", resumen_totales["ventas_confirmadas"]),
            ("Ticket promedio", resumen_totales["ticket_promedio"]),
            ("Subtotal", resumen_totales["subtotal"]),
            ("Descuentos", resumen_totales["descuentos"]),
            ("Impuestos", resumen_totales["impuestos"]),
            ("Envios", resumen_totales["envios"]),
            ("Monto pendiente", resumen_totales["monto_pendiente"]),
            ("Pedidos pendientes", resumen_totales["pedidos_pendientes"]),
        )

        if tipo == "resumen":
            filas = []
            for estado in resumen["estados"]:
                filas.append(
                    (
                        "Estado",
                        "",
                        estado["estado"],
                        estado["cantidad"],
                        estado["monto"],
                    )
                )
            for producto in resumen["productos_mas_vendidos"]:
                filas.append(
                    (
                        "Producto",
                        producto["codigo"],
                        producto["nombre"],
                        producto["cantidad"],
                        producto["ingresos"],
                    )
                )
            return ReporteTabular(
                titulo="Resumen comercial",
                metadata=metadata,
                totales=totales,
                encabezados=("Seccion", "Codigo", "Concepto", "Cantidad", "Monto"),
                filas=tuple(filas),
            )

        if tipo == "ventas":
            pedidos = self._pedidos_periodo(
                self.fecha_desde,
                self.fecha_hasta,
            ).select_related("usuario")
            filas = tuple(
                (
                    self._fecha_local(pedido.fecha_creacion),
                    pedido.numero,
                    self._estado_pedido(pedido),
                    pedido.usuario.email,
                    formatear_monto(pedido.subtotal),
                    formatear_monto(pedido.descuento_total),
                    formatear_monto(pedido.impuesto),
                    formatear_monto(pedido.envio),
                    formatear_monto(pedido.total),
                    pedido.moneda,
                )
                for pedido in pedidos.order_by("fecha_creacion", "id")
            )
            return ReporteTabular(
                titulo="Detalle de ventas",
                metadata=metadata,
                totales=totales,
                encabezados=(
                    "Fecha",
                    "Pedido",
                    "Estado",
                    "Cliente",
                    "Subtotal",
                    "Descuentos",
                    "Impuestos",
                    "Envio",
                    "Total",
                    "Moneda",
                ),
                filas=filas,
            )

        if tipo == "pagos":
            return self._tabla_pagos(metadata)

        return self._tabla_impuestos(metadata, totales)

    def _pedidos_periodo(self, fecha_desde, fecha_hasta):
        inicio, fin_exclusivo = self._limites(fecha_desde, fecha_hasta)
        aprobados = Pago.objects.filter(
            pedido_id=OuterRef("pk"),
            estado=Pago.Estado.APROBADO,
        )
        pendientes = Pago.objects.filter(
            pedido_id=OuterRef("pk"),
            estado=Pago.Estado.PENDIENTE,
        )
        rechazados = Pago.objects.filter(
            pedido_id=OuterRef("pk"),
            estado=Pago.Estado.RECHAZADO,
        )
        return Pedido.objects.filter(
            empresa=self.empresa,
            fecha_creacion__gte=inicio,
            fecha_creacion__lt=fin_exclusivo,
        ).annotate(
            tiene_pago_aprobado=Exists(aprobados),
            tiene_pago_pendiente=Exists(pendientes),
            tiene_pago_rechazado=Exists(rechazados),
        )

    def _pedidos_confirmados(self, pedidos):
        return pedidos.filter(
            Q(estado_pago=Pedido.EstadoPago.PAGADO)
            | Q(tiene_pago_aprobado=True)
        )

    def _totales_confirmados(self, confirmados):
        agregado = confirmados.aggregate(
            ingresos=Sum("total"),
            subtotal=Sum("subtotal"),
            descuentos=Sum("descuento_total"),
            impuestos=Sum("impuesto"),
            envios=Sum("envio"),
            ventas=Count("id"),
        )
        ventas = agregado["ventas"] or 0
        ingresos = agregado["ingresos"] or ZERO
        return {
            "ingresos": ingresos,
            "subtotal": agregado["subtotal"] or ZERO,
            "descuentos": agregado["descuentos"] or ZERO,
            "impuestos": agregado["impuestos"] or ZERO,
            "envios": agregado["envios"] or ZERO,
            "ventas": ventas,
            "ticket_promedio": ingresos / ventas if ventas else ZERO,
        }

    def _estados(self, pedidos):
        acumulados = {
            estado: {"cantidad": 0, "monto": ZERO}
            for estado in ORDEN_ESTADOS
        }
        for pedido in pedidos.only("estado_pago", "total"):
            estado = self._estado_pedido(pedido)
            acumulados[estado]["cantidad"] += 1
            acumulados[estado]["monto"] += pedido.total

        estados = [
            {
                "estado": estado,
                "cantidad": acumulados[estado]["cantidad"],
                "monto": formatear_monto(acumulados[estado]["monto"]),
            }
            for estado in ORDEN_ESTADOS
            if acumulados[estado]["cantidad"]
        ]
        return estados, acumulados

    def _estado_pedido(self, pedido):
        if (
            pedido.estado_pago == Pedido.EstadoPago.PAGADO
            or pedido.tiene_pago_aprobado
        ):
            return "pagado"
        if pedido.estado_pago == Pedido.EstadoPago.CANCELADO:
            return "cancelado"
        if pedido.tiene_pago_pendiente:
            return "pendiente"
        if pedido.tiene_pago_rechazado:
            return "rechazado"
        return "pendiente"

    def _serie(self, confirmados):
        acumulados = {}
        for fecha_creacion, total in confirmados.values_list(
            "fecha_creacion",
            "total",
        ):
            fecha_local = timezone.localtime(
                fecha_creacion,
                self.zona_horaria,
            ).date()
            clave = (
                fecha_local
                if self.agrupacion == "dia"
                else fecha_local.replace(day=1)
            )
            if clave not in acumulados:
                acumulados[clave] = {"ingresos": ZERO, "ventas": 0}
            acumulados[clave]["ingresos"] += total
            acumulados[clave]["ventas"] += 1

        return [
            {
                "periodo": self._periodo_serie(fecha),
                "etiqueta": self._etiqueta_serie(fecha),
                "ingresos": formatear_monto(
                    acumulados.get(fecha, {}).get("ingresos", ZERO)
                ),
                "ventas": acumulados.get(fecha, {}).get("ventas", 0),
            }
            for fecha in self._periodos_serie()
        ]

    def _periodos_serie(self):
        if self.agrupacion == "dia":
            actual = self.fecha_desde
            while actual <= self.fecha_hasta:
                yield actual
                actual += timedelta(days=1)
            return

        actual = self.fecha_desde.replace(day=1)
        ultimo = self.fecha_hasta.replace(day=1)
        while actual <= ultimo:
            yield actual
            actual = (
                actual.replace(year=actual.year + 1, month=1)
                if actual.month == 12
                else actual.replace(month=actual.month + 1)
            )

    def _periodo_serie(self, fecha):
        return fecha.isoformat() if self.agrupacion == "dia" else fecha.strftime("%Y-%m")

    def _etiqueta_serie(self, fecha):
        varios_anios = self.fecha_desde.year != self.fecha_hasta.year
        if self.agrupacion == "mes":
            return f"{MESES[fecha.month]} {fecha.year}" if varios_anios else MESES[fecha.month]
        etiqueta = f"{fecha.day:02d} {MESES[fecha.month]}"
        return f"{etiqueta} {fecha.year}" if varios_anios else etiqueta

    def _productos_mas_vendidos(self, confirmados):
        productos = (
            DetallePedido.objects.filter(pedido__in=confirmados)
            .values("codigo_articulo", "nombre_articulo")
            .annotate(
                cantidad=Sum("cantidad"),
                ingresos=Sum("subtotal_final"),
            )
            .order_by("-cantidad", "-ingresos", "nombre_articulo")[:10]
        )
        return [
            {
                "codigo": producto["codigo_articulo"],
                "nombre": producto["nombre_articulo"],
                "cantidad": producto["cantidad"],
                "ingresos": formatear_monto(producto["ingresos"]),
            }
            for producto in productos
        ]

    def _tabla_pagos(self, metadata):
        pagos = Pago.objects.filter(
            empresa=self.empresa,
            fecha_creacion__gte=self.inicio,
            fecha_creacion__lt=self.fin_exclusivo,
        ).select_related("pedido", "usuario")
        agregado = pagos.values("estado").annotate(
            cantidad=Count("id"),
            monto=Sum("monto"),
        )
        por_estado = {
            item["estado"]: item
            for item in agregado
        }
        totales = tuple(
            (
                f"Pagos {estado}",
                f"{por_estado.get(estado, {}).get('cantidad', 0)} / "
                f"{formatear_monto(por_estado.get(estado, {}).get('monto', ZERO))}",
            )
            for estado in (
                Pago.Estado.APROBADO,
                Pago.Estado.PENDIENTE,
                Pago.Estado.RECHAZADO,
            )
        )
        filas = tuple(
            (
                self._fecha_local(pago.fecha_creacion),
                pago.pedido.numero,
                str(pago.referencia),
                pago.proveedor,
                pago.estado,
                pago.usuario.email,
                formatear_monto(pago.monto),
                pago.moneda,
                self._fecha_local(pago.fecha_confirmacion)
                if pago.fecha_confirmacion
                else "",
            )
            for pago in pagos.order_by("fecha_creacion", "id")
        )
        return ReporteTabular(
            titulo="Detalle de pagos",
            metadata=metadata,
            totales=totales,
            encabezados=(
                "Fecha",
                "Pedido",
                "Referencia",
                "Proveedor",
                "Estado",
                "Cliente",
                "Monto",
                "Moneda",
                "Fecha confirmacion",
            ),
            filas=filas,
        )

    def _tabla_impuestos(self, metadata, totales_resumen):
        confirmados = self._pedidos_confirmados(
            self._pedidos_periodo(self.fecha_desde, self.fecha_hasta)
        ).select_related("usuario")
        filas = tuple(
            (
                self._fecha_local(pedido.fecha_creacion),
                pedido.numero,
                pedido.usuario.email,
                formatear_monto(pedido.subtotal - pedido.descuento_total),
                str(pedido.tasa_impuesto),
                formatear_monto(pedido.impuesto),
                formatear_monto(pedido.total),
                pedido.moneda,
            )
            for pedido in confirmados.order_by("fecha_creacion", "id")
        )
        return ReporteTabular(
            titulo="Detalle de impuestos",
            metadata=metadata,
            totales=totales_resumen,
            encabezados=(
                "Fecha",
                "Pedido",
                "Cliente",
                "Base imponible",
                "Tasa",
                "Impuesto",
                "Total",
                "Moneda",
            ),
            filas=filas,
        )

    def _moneda(self, pedidos):
        return pedidos.values_list("moneda", flat=True).first() or "HNL"

    def _limites(self, fecha_desde, fecha_hasta):
        inicio = datetime.combine(fecha_desde, time.min, self.zona_horaria)
        fin_exclusivo = datetime.combine(
            fecha_hasta + timedelta(days=1),
            time.min,
            self.zona_horaria,
        )
        return inicio, fin_exclusivo

    def _fecha_local(self, valor):
        return timezone.localtime(valor, self.zona_horaria).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    def _variacion(self, actual, anterior):
        if not anterior:
            return None
        porcentaje = ((actual - anterior) / anterior) * Decimal("100")
        return float(porcentaje.quantize(PERCENT_QUANTIZER, rounding=ROUND_HALF_UP))


def exportar_csv(tabla):
    salida = StringIO(newline="")
    escritor = csv.writer(salida)
    escritor.writerow(["Reporte", _limpiar_celda(tabla.titulo)])
    for clave, valor in tabla.metadata:
        escritor.writerow([_limpiar_celda(clave), _limpiar_celda(valor)])
    escritor.writerow([])
    escritor.writerow(["Totales"])
    for clave, valor in tabla.totales:
        escritor.writerow([_limpiar_celda(clave), _limpiar_celda(valor)])
    escritor.writerow([])
    escritor.writerow([_limpiar_celda(valor) for valor in tabla.encabezados])
    for fila in tabla.filas:
        escritor.writerow([_limpiar_celda(valor) for valor in fila])
    return ("\ufeff" + salida.getvalue()).encode("utf-8")


def exportar_xlsx(tabla):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    libro = Workbook()
    hoja = libro.active
    hoja.title = "Reporte"
    hoja.append(["Reporte", _limpiar_celda(tabla.titulo)])
    hoja["A1"].font = Font(bold=True)
    for clave, valor in tabla.metadata:
        hoja.append([_limpiar_celda(clave), _limpiar_celda(valor)])
    hoja.append([])
    hoja.append(["Totales"])
    hoja.cell(row=hoja.max_row, column=1).font = Font(bold=True)
    for clave, valor in tabla.totales:
        hoja.append([_limpiar_celda(clave), _limpiar_celda(valor)])
    hoja.append([])
    hoja.append([_limpiar_celda(valor) for valor in tabla.encabezados])
    fila_encabezados = hoja.max_row
    for celda in hoja[fila_encabezados]:
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = PatternFill("solid", fgColor="2D4B77")
        celda.alignment = Alignment(horizontal="center")
    for fila in tabla.filas:
        hoja.append([_limpiar_celda(valor) for valor in fila])

    hoja.freeze_panes = f"A{fila_encabezados + 1}"
    for columna in hoja.columns:
        ancho = min(
            max(len(str(celda.value or "")) for celda in columna) + 2,
            42,
        )
        hoja.column_dimensions[columna[0].column_letter].width = max(ancho, 12)

    salida = BytesIO()
    libro.save(salida)
    return salida.getvalue()


def exportar_pdf(tabla):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    salida = BytesIO()
    documento = SimpleDocTemplate(
        salida,
        pagesize=landscape(letter),
        rightMargin=24,
        leftMargin=24,
        topMargin=24,
        bottomMargin=24,
        title=tabla.titulo,
    )
    estilos = getSampleStyleSheet()
    celda = ParagraphStyle(
        "CeldaReporte",
        parent=estilos["BodyText"],
        fontSize=6,
        leading=7,
    )
    elementos = [Paragraph(escape(tabla.titulo), estilos["Title"]), Spacer(1, 8)]
    for clave, valor in tabla.metadata:
        elementos.append(
            Paragraph(f"<b>{escape(str(clave))}:</b> {escape(str(valor))}", estilos["BodyText"])
        )
    elementos.append(Spacer(1, 8))
    elementos.append(Paragraph("Totales", estilos["Heading2"]))
    datos_totales = [
        [Paragraph(escape(str(clave)), celda), Paragraph(escape(str(valor)), celda)]
        for clave, valor in tabla.totales
    ]
    tabla_totales = Table(datos_totales, colWidths=[2.4 * inch, 2 * inch])
    tabla_totales.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E8EEF5")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    elementos.extend([tabla_totales, Spacer(1, 12)])

    datos = [
        [Paragraph(f"<b>{escape(str(valor))}</b>", celda) for valor in tabla.encabezados]
    ]
    datos.extend(
        [Paragraph(escape(_limpiar_celda(valor)), celda) for valor in fila]
        for fila in tabla.filas
    )
    ancho_util = landscape(letter)[0] - 48
    anchos = [ancho_util / max(len(tabla.encabezados), 1)] * len(tabla.encabezados)
    tabla_detalle = Table(datos, colWidths=anchos, repeatRows=1)
    tabla_detalle.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2D4B77")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F7FA")]),
            ]
        )
    )
    elementos.append(tabla_detalle)
    documento.build(elementos)
    return salida.getvalue()
