from decimal import Decimal
from html import escape
from io import BytesIO
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.db import transaction
from django.utils import timezone
from reportlab.graphics.barcode import createBarcodeDrawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    Image,
    KeepTogether,
    LongTable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from PIL import Image as PILImage, ImageChops

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


def _color(valor, predeterminado):
    try:
        return colors.HexColor(valor)
    except (TypeError, ValueError):
        return colors.HexColor(predeterminado)


def _color_contraste(color):
    luminancia = (0.299 * color.red) + (0.587 * color.green) + (0.114 * color.blue)
    return colors.black if luminancia > 0.62 else colors.white


def _color_tenue(color, proporcion_blanco=0.92):
    return colors.Color(
        color.red + ((1 - color.red) * proporcion_blanco),
        color.green + ((1 - color.green) * proporcion_blanco),
        color.blue + ((1 - color.blue) * proporcion_blanco),
    )


def _dinero(moneda, monto):
    return f"{moneda} {Decimal(monto):,.2f}"


def _texto_contacto_empresa(empresa):
    valores = [
        empresa.telefono,
        empresa.correo,
        empresa.sitio_web,
        empresa.direccion,
    ]
    return " | ".join(str(valor).strip() for valor in valores if valor)


def _contenido_logo_empresa(empresa):
    if not empresa.logo:
        return None

    try:
        with empresa.logo.open("rb") as archivo_logo:
            contenido = archivo_logo.read()
        return contenido or None
    except Exception:
        # El documento sigue siendo valido si el almacenamiento remoto no responde.
        return None


def _recortar_margenes_logo(contenido):
    try:
        with PILImage.open(BytesIO(contenido)) as original:
            imagen = original.convert("RGBA")
            alpha = imagen.getchannel("A")
            if alpha.getextrema()[0] < 250:
                mascara = alpha.point(lambda valor: 255 if valor > 12 else 0)
            else:
                fondo = PILImage.new("RGB", imagen.size, imagen.getpixel((0, 0))[:3])
                diferencia = ImageChops.difference(imagen.convert("RGB"), fondo)
                mascara = diferencia.convert("L").point(
                    lambda valor: 255 if valor > 12 else 0
                )

            limites = mascara.getbbox()
            if not limites:
                return contenido

            margen = max(2, int(min(imagen.size) * 0.025))
            izquierda, superior, derecha, inferior = limites
            limites_con_margen = (
                max(0, izquierda - margen),
                max(0, superior - margen),
                min(imagen.width, derecha + margen),
                min(imagen.height, inferior + margen),
            )
            recortada = imagen.crop(limites_con_margen)
            salida = BytesIO()
            recortada.save(salida, format="PNG", optimize=True)
            return salida.getvalue()
    except (OSError, ValueError):
        return contenido


def _imagen_logo(contenido):
    if not contenido:
        return None

    try:
        imagen = Image(BytesIO(contenido))
        ancho_maximo = 34 * mm
        alto_maximo = 18 * mm
        escala = min(
            ancho_maximo / imagen.imageWidth,
            alto_maximo / imagen.imageHeight,
        )
        imagen.drawWidth = imagen.imageWidth * escala
        imagen.drawHeight = imagen.imageHeight * escala
        return imagen
    except Exception:
        return None


def _ajustar_fuente(texto, ancho_maximo, fuente="Helvetica", inicial=7):
    tamano = inicial
    while tamano > 5 and stringWidth(texto, fuente, tamano) > ancho_maximo:
        tamano -= 0.5
    return tamano


def _decorar_pagina(
    canvas,
    documento,
    empresa,
    prefactura,
    color_principal,
):
    ancho, alto = A4

    canvas.saveState()
    margen = 14 * mm
    if canvas.getPageNumber() > 1:
        canvas.setStrokeColor(color_principal)
        canvas.setLineWidth(1)
        canvas.line(margen, alto - 12 * mm, ancho - margen, alto - 12 * mm)
        canvas.setFillColor(colors.HexColor("#4B5563"))
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawString(
            margen,
            alto - 9.5 * mm,
            f"Prefactura {prefactura.numero} | Pedido {prefactura.pedido.numero}",
        )

    canvas.setStrokeColor(_color_tenue(color_principal, 0.7))
    canvas.setLineWidth(0.5)
    canvas.line(margen, 13 * mm, ancho - margen, 13 * mm)

    contacto = _texto_contacto_empresa(empresa) or empresa.nombre
    ancho_contacto = ancho - (58 * mm)
    tamano_contacto = _ajustar_fuente(contacto, ancho_contacto)
    canvas.setFillColor(colors.HexColor("#4B5563"))
    canvas.setFont("Helvetica", tamano_contacto)
    canvas.drawString(margen, 8.5 * mm, contacto)
    canvas.setFont("Helvetica-Bold", 7)
    canvas.drawRightString(
        ancho - margen,
        8.5 * mm,
        f"Pagina {canvas.getPageNumber()}",
    )
    canvas.restoreState()


def _campo_documento(etiqueta, valor, estilos):
    return Paragraph(
        f'<font size="7" color="#6B7280">{escape(etiqueta.upper())}</font><br/>'
        f"<b>{escape(str(valor or 'No registrado'))}</b>",
        estilos["Campo"],
    )


def generar_pdf_prefactura(prefactura):
    pedido = prefactura.pedido
    empresa = pedido.empresa
    sucursal = pedido.sucursal_pago
    perfil = getattr(pedido.usuario, "perfil", None)
    zona = ZoneInfo(settings.TIME_ZONE)
    color_principal = _color(empresa.color_principal, "#D1393D")
    color_secundario = _color(empresa.color_secundario, "#E94A51")
    color_acento = _color(empresa.color_acento, "#2D4B77")
    color_texto = _color(empresa.color_texto, "#111827")
    texto_principal = _color_contraste(color_principal)
    fondo_suave = _color_tenue(color_acento, 0.91)
    contenido_logo = _contenido_logo_empresa(empresa)
    if contenido_logo:
        contenido_logo = _recortar_margenes_logo(contenido_logo)

    estilos_base = getSampleStyleSheet()
    estilos = {
        "Empresa": ParagraphStyle(
            "EmpresaPrefactura",
            parent=estilos_base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=19,
            textColor=color_acento,
            spaceAfter=3,
        ),
        "Contacto": ParagraphStyle(
            "ContactoPrefactura",
            parent=estilos_base["BodyText"],
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#4B5563"),
        ),
        "Documento": ParagraphStyle(
            "DocumentoPrefactura",
            parent=estilos_base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=19,
            leading=21,
            alignment=2,
            textColor=color_principal,
        ),
        "Numero": ParagraphStyle(
            "NumeroPrefactura",
            parent=estilos_base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            alignment=2,
            textColor=color_texto,
        ),
        "Leyenda": ParagraphStyle(
            "LeyendaPrefactura",
            parent=estilos_base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=texto_principal,
            alignment=1,
        ),
        "Seccion": ParagraphStyle(
            "SeccionPrefactura",
            parent=estilos_base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            textColor=color_acento,
            spaceBefore=4,
            spaceAfter=5,
        ),
        "Campo": ParagraphStyle(
            "CampoPrefactura",
            parent=estilos_base["BodyText"],
            fontSize=8.5,
            leading=11,
            textColor=color_texto,
        ),
        "Celda": ParagraphStyle(
            "CeldaPrefactura",
            parent=estilos_base["BodyText"],
            fontSize=7.5,
            leading=9.5,
            textColor=color_texto,
        ),
        "CeldaDerecha": ParagraphStyle(
            "CeldaDerechaPrefactura",
            parent=estilos_base["BodyText"],
            fontSize=7.5,
            leading=9.5,
            alignment=2,
            textColor=color_texto,
        ),
        "EncabezadoTabla": ParagraphStyle(
            "EncabezadoTablaPrefactura",
            parent=estilos_base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=8.5,
            alignment=1,
            textColor=_color_contraste(color_acento),
        ),
        "Nota": ParagraphStyle(
            "NotaPrefactura",
            parent=estilos_base["BodyText"],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#374151"),
        ),
        "Estado": ParagraphStyle(
            "EstadoPrefactura",
            parent=estilos_base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=color_principal,
        ),
        "Total": ParagraphStyle(
            "TotalPrefactura",
            parent=estilos_base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=texto_principal,
        ),
        "TotalDerecha": ParagraphStyle(
            "TotalDerechaPrefactura",
            parent=estilos_base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            alignment=2,
            textColor=texto_principal,
        ),
    }

    salida = BytesIO()
    documento = SimpleDocTemplate(
        salida,
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=16 * mm,
        bottomMargin=19 * mm,
        title=f"Prefactura {prefactura.numero}",
        author=empresa.nombre,
        subject=f"Pedido {pedido.numero}",
        pageCompression=0,
        invariant=1,
    )

    fecha_pedido = timezone.localtime(pedido.fecha_creacion, zona)
    fecha_vencimiento = timezone.localtime(prefactura.fecha_vencimiento, zona)
    nombre_comprador = pedido.usuario.get_full_name() or pedido.usuario.username
    identidad = perfil.numero_identidad if perfil else ""
    telefono_comprador = (
        (perfil.telefono if perfil else "") or pedido.telefono_recibe
    )
    estado = (
        "Pendiente de pago en sucursal"
        if pedido.estado_pago == Pedido.EstadoPago.PENDIENTE
        and pedido.metodo_pago == Pedido.MetodoPago.SUCURSAL
        else pedido.get_estado_pago_display()
    )
    metodo_pago = pedido.get_metodo_pago_display()
    nombre_sucursal = sucursal.nombre if sucursal else "No aplica"
    direccion_sucursal = sucursal.direccion if sucursal else "No aplica"

    logo = _imagen_logo(contenido_logo)
    identidad_empresa = []
    if logo:
        identidad_empresa.extend([logo, Spacer(1, 2 * mm)])
    identidad_empresa.append(Paragraph(escape(empresa.nombre), estilos["Empresa"]))
    contacto_encabezado = "<br/>".join(
        escape(str(valor))
        for valor in [
            empresa.direccion,
            empresa.telefono,
            empresa.correo,
            empresa.sitio_web,
        ]
        if valor
    )
    if contacto_encabezado:
        identidad_empresa.append(
            Paragraph(contacto_encabezado, estilos["Contacto"])
        )

    cabecera = Table(
        [
            [
                identidad_empresa,
                [
                    Paragraph("PREFACTURA", estilos["Documento"]),
                    Paragraph(
                        escape(prefactura.numero),
                        estilos["Numero"],
                    ),
                ],
            ]
        ],
        colWidths=[112 * mm, 70 * mm],
    )
    cabecera.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (0, 0), 0),
                ("RIGHTPADDING", (0, 0), (0, 0), 5 * mm),
                ("LEFTPADDING", (1, 0), (1, 0), 4 * mm),
                ("RIGHTPADDING", (1, 0), (1, 0), 0),
                ("LINEBEFORE", (1, 0), (1, 0), 2, color_secundario),
            ]
        )
    )

    leyenda = Table(
        [[Paragraph(Prefactura.LEYENDA, estilos["Leyenda"])]],
        colWidths=[182 * mm],
    )
    leyenda.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), color_principal),
                ("BOX", (0, 0), (-1, -1), 0.8, color_principal),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    datos_documento = Table(
        [
            [
                _campo_documento("Numero de prefactura", prefactura.numero, estilos),
                _campo_documento("Numero de pedido", pedido.numero, estilos),
            ],
            [
                _campo_documento(
                    "Fecha y hora",
                    fecha_pedido.strftime("%d/%m/%Y %H:%M"),
                    estilos,
                ),
                _campo_documento("Estado", estado, estilos),
            ],
            [
                _campo_documento(
                    "Fecha de vencimiento",
                    fecha_vencimiento.strftime("%d/%m/%Y %H:%M"),
                    estilos,
                ),
                _campo_documento("Metodo de pago", metodo_pago, estilos),
            ],
            [
                _campo_documento("Sucursal seleccionada", nombre_sucursal, estilos),
                _campo_documento("Direccion de sucursal", direccion_sucursal, estilos),
            ],
        ],
        colWidths=[91 * mm, 91 * mm],
    )
    datos_documento.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, fondo_suave]),
                ("BOX", (0, 0), (-1, -1), 0.5, _color_tenue(color_acento, 0.65)),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, _color_tenue(color_acento, 0.75)),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    datos_comprador = Table(
        [
            [
                _campo_documento("Nombre", nombre_comprador, estilos),
                _campo_documento(
                    "Identidad",
                    identidad or "No registrada",
                    estilos,
                ),
            ],
            [
                _campo_documento(
                    "Telefono",
                    telefono_comprador or "No registrado",
                    estilos,
                ),
                _campo_documento("Correo", pedido.usuario.email, estilos),
            ],
        ],
        colWidths=[91 * mm, 91 * mm],
    )
    datos_comprador.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.5, _color_tenue(color_acento, 0.65)),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, _color_tenue(color_acento, 0.75)),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    encabezados = [
        "Codigo",
        "Producto, servicio o examen",
        "Cantidad",
        "Precio unitario",
        "Descuento",
        "Subtotal",
    ]
    datos_articulos = [
        [Paragraph(escape(valor), estilos["EncabezadoTabla"]) for valor in encabezados]
    ]
    for detalle in pedido.detalles.all():
        datos_articulos.append(
            [
                Paragraph(escape(detalle.codigo_articulo), estilos["Celda"]),
                Paragraph(
                    escape(detalle.nombre_articulo or detalle.nombre_producto),
                    estilos["Celda"],
                ),
                Paragraph(str(detalle.cantidad), estilos["CeldaDerecha"]),
                Paragraph(
                    _dinero(pedido.moneda, detalle.precio_unitario),
                    estilos["CeldaDerecha"],
                ),
                Paragraph(
                    _dinero(pedido.moneda, detalle.descuento_total),
                    estilos["CeldaDerecha"],
                ),
                Paragraph(
                    _dinero(pedido.moneda, detalle.subtotal_final),
                    estilos["CeldaDerecha"],
                ),
            ]
        )

    tabla_articulos = LongTable(
        datos_articulos,
        colWidths=[20 * mm, 64 * mm, 15 * mm, 28 * mm, 25 * mm, 30 * mm],
        repeatRows=1,
        splitByRow=1,
    )
    tabla_articulos.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), color_acento),
                ("BOX", (0, 0), (-1, -1), 0.6, color_acento),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, fondo_suave]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    totales = [
        ("Subtotal", pedido.subtotal),
        ("Descuentos", pedido.descuento_total),
        ("Impuesto", pedido.impuesto),
        ("Envio", pedido.envio),
        ("TOTAL", pedido.total),
    ]
    datos_totales = []
    for etiqueta, monto in totales:
        es_total = etiqueta == "TOTAL"
        datos_totales.append(
            [
                Paragraph(
                    escape(etiqueta),
                    estilos["Total"] if es_total else estilos["Campo"],
                ),
                Paragraph(
                    escape(_dinero(pedido.moneda, monto)),
                    (
                        estilos["TotalDerecha"]
                        if es_total
                        else estilos["CeldaDerecha"]
                    ),
                ),
            ]
        )
    tabla_totales = Table(
        datos_totales,
        colWidths=[42 * mm, 42 * mm],
        hAlign="RIGHT",
    )
    tabla_totales.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, color_acento),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB")),
                ("BACKGROUND", (0, 0), (-1, -2), colors.white),
                ("BACKGROUND", (0, -1), (-1, -1), color_principal),
                ("TEXTCOLOR", (0, -1), (-1, -1), texto_principal),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    qr = createBarcodeDrawing(
        "QR",
        value=f"prefactura:{prefactura.numero}|pedido:{pedido.numero}",
        width=27 * mm,
        height=27 * mm,
    )
    cierre = Table(
        [
            [
                [
                    Paragraph(escape(estado), estilos["Estado"]),
                    Spacer(1, 2 * mm),
                    Paragraph(
                        "Presenta esta prefactura en la sucursal seleccionada "
                        "antes de su vencimiento.",
                        estilos["Nota"],
                    ),
                    Spacer(1, 2 * mm),
                    Paragraph(
                        "El codigo QR identifica este pedido y no constituye "
                        "una autorizacion de pago.",
                        estilos["Nota"],
                    ),
                ],
                qr,
            ]
        ],
        colWidths=[150 * mm, 32 * mm],
    )
    cierre.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), fondo_suave),
                ("BOX", (0, 0), (-1, -1), 0.6, color_acento),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("ALIGN", (1, 0), (1, 0), "CENTER"),
            ]
        )
    )

    elementos = [
        cabecera,
        Spacer(1, 5 * mm),
        leyenda,
        Spacer(1, 4 * mm),
        Paragraph("Datos de la prefactura", estilos["Seccion"]),
        datos_documento,
        Spacer(1, 3 * mm),
        Paragraph("Datos del comprador", estilos["Seccion"]),
        datos_comprador,
        Spacer(1, 4 * mm),
        Paragraph("Detalle de articulos", estilos["Seccion"]),
        tabla_articulos,
        Spacer(1, 4 * mm),
        KeepTogether(
            [
                tabla_totales,
                Spacer(1, 4 * mm),
                cierre,
            ]
        ),
    ]

    def decorar(canvas, doc):
        _decorar_pagina(
            canvas,
            doc,
            empresa,
            prefactura,
            color_principal,
        )

    documento.build(elementos, onFirstPage=decorar, onLaterPages=decorar)
    return salida.getvalue()


def enviar_prefactura_por_correo(prefactura, es_reenvio=False):
    correo = correo_comprador_verificado(prefactura.pedido)
    with transaction.atomic():
        bloqueada = Prefactura.objects.select_for_update().get(pk=prefactura.pk)
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
