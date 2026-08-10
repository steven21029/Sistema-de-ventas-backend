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

```http
POST /api/v1/pagos/iniciar/
Content-Type: application/json

{
  "pedido_id": 123
}
```

La ruta, el cuerpo y la integracion actual se conservan. Los nuevos intentos
quedan identificados con `metodo="en_linea"`.

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
    "correo_destino": "s***@correo.com"
  }
}
```

Repetir la solicitud no crea otro pedido, pago ni prefactura, y tampoco envia
de nuevo el correo inicial. El pedido y el pago permanecen pendientes. El
inventario no cambia hasta la confirmacion administrativa.

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

El PDF contiene la leyenda `PREFACTURA - NO ES COMPROBANTE FISCAL`, empresa,
sucursal, comprador, pedido, productos o servicios, cantidades, precios,
subtotal, descuentos, impuestos, envio, total, estado y vencimiento.

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
falla el envio. El limite total incluye el correo inicial.

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

## Variables de entorno

```env
PREFACTURA_VIGENCIA_HORAS=48
PREFACTURA_MAX_INTENTOS_CORREO=4
```

`PREFACTURA_MAX_INTENTOS_CORREO` cuenta el envio inicial y los reenvios. El
correo y el PDF adjunto se envian mediante la API HTTPS de Brevo.

## Integracion del frontend

- Para pago en sucursal, enviar solo `sucursal_id` y usar la respuesta oficial.
- Mostrar `prefactura.url_pdf` como descarga autenticada.
- No enviar correos ni direcciones alternativas desde el navegador.
- Tratar respuestas `200` y `201` del inicio como exito.
- Tras la confirmacion administrativa, refrescar el pedido y el inventario.
- Mantener el flujo actual de `/pagos/iniciar/` para pago en linea.
