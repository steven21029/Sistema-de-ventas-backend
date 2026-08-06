from html import escape
from io import BytesIO
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.db import transaction
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .models import Pedido, Prefactura


class LimiteIntentosCorreoPrefactura(Exception):
    pass


class ErrorEnvioCorreoPrefactura(Exception):
    pass


def correo_comprador_verificado(pedido):
    perfil = getattr(pedido.usuario, "perfil", None)
    correo = pedido.usuario.email.strip()
    if not perfil or not perfil.correo_verificado or not correo:
        raise ValidationError(
            {"correo": "El comprador no tiene un correo verificado disponible."}
        )
    return correo


def enmascarar_correo(correo):
    local, separador, dominio = correo.partition("@")
    if not separador:
        return "***"
    visible = local[:1] if local else ""
    return f"{visible}***@{dominio}"


def generar_pdf_prefactura(prefactura):
    pedido = prefactura.pedido
    empresa = pedido.empresa
    sucursal = pedido.sucursal_pago
    zona = ZoneInfo(settings.TIME_ZONE)
    estilos = getSampleStyleSheet()
    estilo_celda = ParagraphStyle(
        "CeldaPrefactura",
        parent=estilos["BodyText"],
        fontSize=8,
        leading=10,
    )
    estilo_leyenda = ParagraphStyle(
        "LeyendaPrefactura",
        parent=estilos["Heading2"],
        textColor=colors.HexColor("#B42318"),
        alignment=1,
        spaceAfter=10,
    )
    salida = BytesIO()
    documento = SimpleDocTemplate(
        salida,
        pagesize=letter,
        rightMargin=30,
        leftMargin=30,
        topMargin=28,
        bottomMargin=28,
        title=f"Prefactura {prefactura.numero}",
        pageCompression=0,
    )

    fecha_pedido = timezone.localtime(pedido.fecha_creacion, zona)
    fecha_vencimiento = timezone.localtime(prefactura.fecha_vencimiento, zona)
    nombre_comprador = pedido.usuario.get_full_name() or pedido.usuario.username
    estado = (
        "Pendiente de pago en sucursal"
        if pedido.estado_pago == Pedido.EstadoPago.PENDIENTE
        else pedido.get_estado_pago_display()
    )
    elementos = [
        Paragraph(Prefactura.LEYENDA, estilo_leyenda),
        Paragraph(f"Prefactura {escape(prefactura.numero)}", estilos["Title"]),
        Spacer(1, 8),
        Paragraph(f"<b>Empresa:</b> {escape(empresa.nombre)}", estilos["BodyText"]),
        Paragraph(
            f"<b>Sucursal:</b> {escape(sucursal.nombre if sucursal else 'No aplica')}",
            estilos["BodyText"],
        ),
        Paragraph(
            f"<b>Direccion:</b> {escape(sucursal.direccion if sucursal else empresa.direccion)}",
            estilos["BodyText"],
        ),
        Spacer(1, 6),
        Paragraph(f"<b>Comprador:</b> {escape(nombre_comprador)}", estilos["BodyText"]),
        Paragraph(
            f"<b>Correo:</b> {escape(pedido.usuario.email)}",
            estilos["BodyText"],
        ),
        Paragraph(f"<b>Pedido:</b> {escape(pedido.numero)}", estilos["BodyText"]),
        Paragraph(
            f"<b>Fecha del pedido:</b> {fecha_pedido.strftime('%Y-%m-%d %H:%M')}",
            estilos["BodyText"],
        ),
        Paragraph(
            f"<b>Fecha de vencimiento:</b> {fecha_vencimiento.strftime('%Y-%m-%d %H:%M')}",
            estilos["BodyText"],
        ),
        Paragraph(f"<b>Estado:</b> {escape(estado)}", estilos["BodyText"]),
        Spacer(1, 12),
    ]

    datos = [
        [
            Paragraph("<b>Codigo</b>", estilo_celda),
            Paragraph("<b>Producto o servicio</b>", estilo_celda),
            Paragraph("<b>Cantidad</b>", estilo_celda),
            Paragraph("<b>Precio</b>", estilo_celda),
            Paragraph("<b>Total</b>", estilo_celda),
        ]
    ]
    for detalle in pedido.detalles.all():
        datos.append(
            [
                Paragraph(escape(detalle.codigo_articulo), estilo_celda),
                Paragraph(
                    escape(detalle.nombre_articulo or detalle.nombre_producto),
                    estilo_celda,
                ),
                Paragraph(str(detalle.cantidad), estilo_celda),
                Paragraph(
                    f"{pedido.moneda} {detalle.precio_unitario_final:.2f}",
                    estilo_celda,
                ),
                Paragraph(
                    f"{pedido.moneda} {detalle.subtotal_final:.2f}",
                    estilo_celda,
                ),
            ]
        )
    tabla_detalles = Table(
        datos,
        colWidths=[1.05 * inch, 2.65 * inch, 0.7 * inch, 1.05 * inch, 1.05 * inch],
        repeatRows=1,
    )
    tabla_detalles.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.35, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2D4B77")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    elementos.extend([tabla_detalles, Spacer(1, 12)])

    totales = [
        ("Subtotal", pedido.subtotal),
        ("Descuentos", pedido.descuento_total),
        ("Impuestos", pedido.impuesto),
        ("Envio", pedido.envio),
        ("Total", pedido.total),
    ]
    tabla_totales = Table(
        [
            [
                Paragraph(f"<b>{escape(etiqueta)}</b>", estilo_celda),
                Paragraph(f"{pedido.moneda} {monto:.2f}", estilo_celda),
            ]
            for etiqueta, monto in totales
        ],
        colWidths=[1.5 * inch, 1.4 * inch],
        hAlign="RIGHT",
    )
    tabla_totales.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.35, colors.grey),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E8EEF5")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    elementos.extend(
        [
            tabla_totales,
            Spacer(1, 12),
            Paragraph(
                "Presenta esta prefactura en la sucursal seleccionada antes de su vencimiento.",
                estilos["BodyText"],
            ),
        ]
    )
    documento.build(elementos)
    return salida.getvalue()


def enviar_prefactura_por_correo(prefactura, es_reenvio=False):
    correo = correo_comprador_verificado(prefactura.pedido)
    with transaction.atomic():
        bloqueada = (
            Prefactura.objects.select_for_update()
            .get(pk=prefactura.pk)
        )
        if not es_reenvio and bloqueada.intentos_correo:
            return False
        if bloqueada.intentos_correo >= settings.PREFACTURA_MAX_INTENTOS_CORREO:
            raise LimiteIntentosCorreoPrefactura(
                "Se alcanzo el limite de intentos de correo para esta prefactura."
            )
        bloqueada.intentos_correo += 1
        bloqueada.fecha_ultimo_intento_correo = timezone.now()
        bloqueada.save(
            update_fields=[
                "intentos_correo",
                "fecha_ultimo_intento_correo",
                "fecha_actualizacion",
            ]
        )

    pdf = generar_pdf_prefactura(prefactura)
    nombre_archivo = f"prefactura-{prefactura.pedido.numero}.pdf"
    mensaje = EmailMessage(
        subject=f"Prefactura para pago en sucursal {prefactura.pedido.numero}",
        body=(
            "Adjuntamos la prefactura de tu pedido para pagar en la sucursal "
            "seleccionada. Este documento no es un comprobante fiscal."
        ),
        from_email=None,
        to=[correo],
    )
    mensaje.attach(nombre_archivo, pdf, "application/pdf")
    try:
        mensaje.send(fail_silently=False)
    except Exception as exc:
        raise ErrorEnvioCorreoPrefactura(
            "No fue posible enviar la prefactura por correo."
        ) from exc

    Prefactura.objects.filter(pk=prefactura.pk).update(
        correo_enviado_en=timezone.now(),
        fecha_actualizacion=timezone.now(),
    )
    prefactura.refresh_from_db()
    return True
