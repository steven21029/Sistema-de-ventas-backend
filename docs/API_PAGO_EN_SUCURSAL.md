# API de pago en sucursal y prefactura

Contrato para iniciar y confirmar pagos presenciales sin alterar el flujo de
pago en linea. Todas las rutas funcionan con las bases `/api/v1/` y `/api/`.

## Autenticacion

Enviar el access token JWT:

```http
Authorization: Bearer <access_token>
```

El comprador solo puede gestionar sus propios pedidos. La confirmacion exige
superusuario, administrador maestro autorizado, administrador de empresa o
gerente de la empresa del pago.

## Pago en linea existente

El checkout debe mostrar esta opcion solo si la empresa publica devuelve
`pago_en_linea_disponible=true`.

```http
POST /api/v1/pagos/iniciar/
Content-Type: application/json

{
  "pedido_id": 123
}
```

La ruta, el cuerpo y la integracion actual se conservan. Los nuevos intentos
quedan identificados con `metodo="en_linea"`. Si la empresa no tiene pago en
linea activo o le faltan credenciales, la API responde `400` con la clave
`pago_en_linea`.

## Iniciar pago en sucursal

El selector debe cargarse desde el listado publico de sucursales activas:

```http
GET /api/v1/empresas/sucursales/?empresa_slug=Analiza
```

Cada elemento incluye `id`, `nombre`, direccion y demas datos publicos. El
valor de `id` seleccionado se envia como `sucursal_id`; nunca debe enviarse
`null`.

```http
POST /api/v1/pedidos/pedidos/123/pago-en-sucursal/
Content-Type: application/json

{
  "sucursal_id": 5
}
```

Requisitos:

- El usuario debe ser el comprador propietario del pedido.
- El perfil y el correo del comprador deben estar verificados y activos.
- El pedido debe estar pendiente y no haber elegido otro metodo.
- La sucursal debe estar activa y pertenecer a la empresa del pedido.

Respuesta `201 Created` al crear el flujo y `200 OK` al recuperar el mismo
flujo de forma idempotente:

```json
{
  "pedido": {
    "id": 123,
    "numero": "PED-001",
    "estado_pago": "pendiente",
    "metodo_pago": "sucursal"
  },
  "pago": {
    "referencia": "550e8400-e29b-41d4-a716-446655440000",
    "estado": "pendiente",
    "metodo": "sucursal"
  },
  "prefactura": {
    "numero": "PF-PED-001",
    "url_pdf": "/api/v1/pedidos/pedidos/123/prefactura/pdf/",
    "correo_enviado": true,
    "correo_destino": "s***@correo.com",
    "fecha_vencimiento": "2026-08-16T10:30:00-06:00",
    "vigencia_horas": 72,
    "vigente": true,
    "mensaje_vigencia": "Esta prefactura estara disponible durante 72 horas..."
  }
}
```

Repetir la solicitud no crea otro pedido, pago ni prefactura, y tampoco envia
de nuevo el correo inicial. El pedido y el pago permanecen pendientes. El
inventario no cambia hasta la confirmacion administrativa.

## Vigencia y rechazo automatico

La prefactura permanece vigente durante 72 horas contadas desde su emision.
Durante ese plazo se respetan los precios y el total historico del pedido. Si
el personal autorizado no confirma el pago antes de `fecha_vencimiento`, el
backend cambia automaticamente:

- `pedido.estado_pago` de `pendiente` a `rechazado`.
- Todo intento relacionado que siga pendiente a `estado=rechazado`.
- `pago.codigo_respuesta` a `PREFACTURA_VENCIDA`.

El vencimiento es idempotente y no descuenta ni modifica inventario. Una
prefactura vencida conserva su PDF como documento historico, claramente
marcado como rechazado, pero no puede reenviarse ni confirmarse. El comprador
debe realizar una nueva compra.

Los listados de pedidos y pagos, los reportes y las acciones de prefactura
actualizan los vencimientos antes de responder. En produccion tambien debe
programarse periodicamente:

```powershell
python manage.py vencer_prefacturas_sucursal
```

Puede limitarse a una empresa con `--empresa-slug=Analiza`.

Errores principales:

| Estado | Caso |
|---|---|
| `400` | Pedido no pagable, correo no verificado, sucursal invalida o metodo ya seleccionado |
| `403` | Usuario autenticado sin permiso para gestionar el pago |
| `404` | Pedido inexistente o ajeno |
| `503` | El proveedor de correo no pudo entregar la prefactura |

## Descargar prefactura

```http
GET /api/v1/pedidos/pedidos/123/prefactura/pdf/
```

Respuesta:

```http
Content-Type: application/pdf
Content-Disposition: attachment; filename="prefactura-PED-001.pdf"
```

El PDF se genera en formato A4 vertical y contiene la leyenda
`PREFACTURA - NO ES COMPROBANTE FISCAL`. La identidad visual se obtiene de la
empresa asociada al pedido: logo, nombre, colores, telefono, correo, direccion
y sitio web. Ningun dato de marca esta fijado para una empresa particular.

El documento incluye:

- Logo de la empresa en el encabezado, con recorte automatico de margenes
  vacios. El documento no incluye marca de agua.
- Numeros de prefactura y pedido, fecha y hora, estado, vencimiento, metodo de
  pago y sucursal seleccionada.
- Nombre, identidad cuando exista, telefono y correo del comprador.
- Codigo, articulo, cantidad, precio unitario, descuento y subtotal por linea.
- Subtotal, descuentos, impuesto, envio y total oficiales del pedido.
- Codigo QR que identifica la prefactura y el pedido.
- Contacto de la empresa y numero de pagina en el pie.
- Encabezados de tabla repetidos y filas indivisibles cuando hay varias paginas.

El correo y la descarga usan el mismo generador determinista. Para una misma
prefactura y datos de pedido, el archivo adjunto es exactamente igual al que
devuelve este endpoint.

## Reenviar prefactura

```http
POST /api/v1/pedidos/pedidos/123/prefactura/reenviar-correo/
```

No recibe una direccion en el cuerpo. El backend usa exclusivamente el correo
verificado de la cuenta propietaria.

```json
{
  "correo_enviado": true,
  "correo_destino": "s***@correo.com",
  "intentos_restantes": 2
}
```

Devuelve `429 Too Many Requests` al alcanzar el limite configurado y `503` si
falla el envio. Una prefactura vencida devuelve `400`. El limite total incluye
el correo inicial.

## Confirmar pago en sucursal

```http
POST /api/v1/pagos/550e8400-e29b-41d4-a716-446655440000/confirmar-en-sucursal/
```

No requiere cuerpo. Solo acepta pagos con proveedor y metodo `sucursal` que
pertenezcan a una empresa administrable por el usuario.

```json
{
  "pago": {
    "referencia": "550e8400-e29b-41d4-a716-446655440000",
    "estado": "aprobado",
    "metodo": "sucursal"
  },
  "pedido": {
    "id": 123,
    "numero": "PED-001",
    "estado_pago": "pagado",
    "metodo_pago": "sucursal"
  },
  "duplicado": false
}
```

La confirmacion valida y descuenta inventario mediante el mismo efecto
comercial usado por los pagos aprobados en linea. Una segunda confirmacion
devuelve `200 OK`, `duplicado=true` y no repite el movimiento de inventario.
Si falta inventario, responde `400` y la transaccion conserva pago y pedido
como pendientes.

Cuando las 72 horas ya finalizaron, responde `400`; antes de responder deja el
pedido y el intento en `rechazado`, sin ejecutar efectos de inventario.

## Cancelar un pedido pendiente

```http
POST /api/v1/pedidos/pedidos/123/cancelar-pendiente/
Content-Type: application/json

{
  "motivo": "Pedido abandonado por el cliente"
}
```

Solo puede usarlo un superusuario, administrador maestro autorizado,
administrador de empresa o gerente de la empresa del pedido. El pedido debe
seguir con `estado_pago=pendiente` y no puede tener pagos aprobados.

Respuesta `200 OK`:

```json
{
  "pedido": {
    "id": 123,
    "estado_pago": "cancelado",
    "metodo_pago": "sucursal",
    "motivo_cancelacion": "Pedido abandonado por el cliente",
    "cancelado_por": 8,
    "cancelado_por_email": "admin@example.com",
    "fecha_cancelacion": "2026-08-10T14:30:00-06:00",
    "inventario_descontado": false
  },
  "pagos_cancelados": [
    {
      "referencia": "550e8400-e29b-41d4-a716-446655440000",
      "pedido": 123,
      "metodo": "sucursal",
      "estado": "cancelado",
      "monto": "123.50"
    }
  ],
  "duplicado": false
}
```

La operacion bloquea pedido e intentos dentro de una transaccion. Solo cambia
intentos que todavia esten `pendiente`; conserva rechazados como historial y
no crea movimientos de inventario. Repetirla devuelve `duplicado=true`, el
mismo motivo y la misma auditoria. Un pedido pagado o con pago aprobado recibe
`400`, un comprador recibe `403` y un administrador de otra empresa recibe
`403`.

Esta accion no reemplaza la confirmacion presencial. La unica ruta que puede
aprobar administrativamente un pago en sucursal sigue siendo:

```http
POST /api/v1/pagos/{referencia}/confirmar-en-sucursal/
```

Los listados administrativos exponen los campos necesarios:

- `GET /api/v1/pedidos/pedidos/` incluye `metodo_pago`, motivo, administrador y
  fecha de cancelacion.
- `GET /api/v1/pagos/` incluye `metodo`, `estado`, `referencia`, `pedido` y
  `monto`.

## Variables de entorno

```env
PREFACTURA_VIGENCIA_HORAS=72
PREFACTURA_MAX_INTENTOS_CORREO=4
```

`PREFACTURA_MAX_INTENTOS_CORREO` cuenta el envio inicial y los reenvios. El
correo y el PDF adjunto se envian mediante la API HTTPS de Brevo.

## Integracion del frontend

- Para pago en sucursal, enviar solo `sucursal_id` y usar la respuesta oficial.
- Mostrar `prefactura.mensaje_vigencia`, `fecha_vencimiento` y un contador
  informativo calculado en la zona horaria del navegador.
- Considerar siempre `estado_pago=rechazado` como no pagable; no habilitar
  confirmacion ni reenvio y solicitar una nueva compra.
- Mostrar `prefactura.url_pdf` como descarga autenticada.
- No enviar correos ni direcciones alternativas desde el navegador.
- Tratar respuestas `200` y `201` del inicio como exito.
- Tras la confirmacion administrativa, refrescar el pedido y el inventario.
- Tras cancelar un pendiente, retirar el pedido de acciones confirmables y
  refrescar los agregados del resumen comercial.
- Mantener el flujo actual de `/pagos/iniciar/` para pago en linea.
