from django.conf import settings


def construir_aviso_legal(empresa):
    nombre = empresa.nombre
    contacto = empresa.correo or empresa.telefono or empresa.sitio_web or "No registrado"
    return {
        "empresa": {
            "nombre": nombre,
            "slug": empresa.slug,
            "telefono": empresa.telefono,
            "correo": empresa.correo,
            "direccion": empresa.direccion,
            "sitio_web": empresa.sitio_web,
        },
        "documentos": {
            "terminos": {
                "titulo": "Terminos y condiciones",
                "version": settings.TERMINOS_VERSION_ACTUAL,
            },
            "privacidad": {
                "titulo": "Politica de privacidad",
                "version": settings.PRIVACIDAD_VERSION_ACTUAL,
            },
        },
        "consentimientos": {
            "terminos_y_privacidad": {
                "obligatorio": True,
                "campo_combinado": "acepta_terminos_privacidad",
                "campos_compatibles": ["acepta_terminos", "acepta_privacidad"],
                "etiqueta": (
                    "Acepto los terminos y condiciones y la politica de privacidad."
                ),
            },
            "promociones": {
                "obligatorio": False,
                "campo": "acepta_promociones",
                "valor_predeterminado": False,
                "canales": ["correo", "telefono"],
                "etiqueta": (
                    "Deseo recibir promociones y novedades por correo y telefono."
                ),
            },
        },
        "secciones": [
            {
                "clave": "responsable",
                "titulo": "Responsable del tratamiento",
                "contenido": (
                    f"{nombre} es responsable del tratamiento de los datos "
                    f"proporcionados en esta plataforma. Contacto: {contacto}."
                ),
            },
            {
                "clave": "tratamiento",
                "titulo": "Tratamiento de datos",
                "contenido": (
                    "Los datos se utilizan para crear y proteger la cuenta, gestionar "
                    "compras, pagos, prefacturas, entregas, atencion al cliente y las "
                    "obligaciones administrativas asociadas al servicio."
                ),
            },
            {
                "clave": "conservacion",
                "titulo": "Conservacion",
                "contenido": (
                    "La informacion se conserva durante la relacion con la empresa y "
                    "posteriormente durante los plazos necesarios para atender "
                    "obligaciones legales, fiscales, contables, de seguridad y defensa "
                    "de reclamaciones. Los consentimientos y sus retiros se conservan "
                    "como evidencia de cumplimiento."
                ),
            },
            {
                "clave": "proveedores",
                "titulo": "Proveedores de servicio",
                "contenido": (
                    "La empresa puede utilizar proveedores de infraestructura, base de "
                    "datos, almacenamiento, correo transaccional y procesamiento de "
                    "pagos. Solo reciben la informacion necesaria para prestar su "
                    "servicio y deben aplicar medidas de confidencialidad y seguridad."
                ),
            },
            {
                "clave": "derechos",
                "titulo": "Derechos del titular",
                "contenido": (
                    "El titular puede solicitar acceso, correccion, actualizacion o "
                    "eliminacion cuando corresponda, oponerse a usos no obligatorios y "
                    "retirar en cualquier momento el consentimiento para promociones "
                    "sin afectar sus compras ni los mensajes transaccionales."
                ),
            },
            {
                "clave": "compras",
                "titulo": "Compras y comunicaciones necesarias",
                "contenido": (
                    "Los pedidos conservan sus datos comerciales oficiales. La empresa "
                    "puede enviar codigos de seguridad, recuperacion de cuenta, estados "
                    "de compra, prefacturas y avisos indispensables aunque no se hayan "
                    "aceptado promociones."
                ),
            },
            {
                "clave": "uso_sanitario",
                "titulo": "Informacion relacionada con servicios sanitarios",
                "contenido": (
                    "Cuando una compra incluya examenes o servicios de salud, la "
                    "informacion se tratara con confidencialidad reforzada y solo para "
                    "coordinar, prestar y respaldar el servicio solicitado. La "
                    "plataforma comercial no sustituye la evaluacion de un profesional "
                    "de la salud."
                ),
            },
            {
                "clave": "promociones",
                "titulo": "Promociones opcionales",
                "contenido": (
                    "La publicidad por correo o telefono solo se permite cuando el "
                    "usuario la acepta expresamente. La preferencia puede retirarse "
                    "desde la cuenta y el backend excluira al usuario de futuras "
                    "comunicaciones promocionales."
                ),
            },
        ],
    }
