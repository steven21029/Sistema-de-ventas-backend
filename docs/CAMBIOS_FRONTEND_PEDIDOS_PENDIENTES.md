# Cambios frontend: reportes y pedidos pendientes

Estado: backend implementado y verificado localmente el 10 de agosto de 2026.

Este documento contiene los cambios que debe integrar el panel administrativo.
Todas las rutas funcionan bajo `/api/v1/` y `/api/`; el frontend debe preferir
`/api/v1/`.

## 1. Resumen comercial ampliado

Ruta existente:

```http
GET /api/v1/reportes/resumen-ventas/?empresa_slug=analiza&fecha_desde=2026-08-01&fecha_hasta=2026-08-31&agrupacion=mes&comparar_periodo_anterior=true
Authorization: Bearer ACCESS_TOKEN
```

Dentro de `resumen` se agregaron estos objetos:

```json
{
  "resumen": {
    "pagos_por_metodo": {
      "sucursal": {
        "cantidad": 12,
        "monto": "9000.00"
      },
      "en_linea": {
        "cantidad": 20,
        "monto": "16000.00"
      }
    },
    "pendientes_por_metodo": {
      "sucursal": {
        "cantidad": 3,
        "monto": "2100.00"
      },
      "en_linea": {
        "cantidad": 1,
        "monto": "900.00"
      },
      "sin_metodo": {
        "cantidad": 1,
        "monto": "500.00"
      }
    }
  }
}
```

Reglas para el frontend:

- No recalcular estos valores usando pedidos o intentos de pago.
- `pagos_por_metodo` contiene solamente pagos confirmados.
- `pendientes_por_metodo` contiene pedidos cuyo `estado_pago` sigue en
  `pendiente` y no tienen pagos aprobados.
- Los pedidos se cuentan una sola vez aunque tengan varios intentos.
- Las claves siempre existen, incluso cuando su cantidad y monto son cero.
- Los montos son cadenas decimales; no tratarlos como valores de punto flotante.
- `sin_metodo` representa `metodo_pago="pendiente"` o metodo aun no elegido.

## 2. Cancelar un pedido pendiente

Nueva ruta administrativa:

```http
POST /api/v1/pedidos/pedidos/{pedido_id}/cancelar-pendiente/
Authorization: Bearer ACCESS_TOKEN
Content-Type: application/json
```

Cuerpo:

```json
{
  "motivo": "Pedido abandonado por el cliente"
}
```

Respuesta `200 OK`:

```json
{
  "pedido": {
    "id": 123,
    "numero": "PED-001",
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
      "id": 45,
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

Comportamiento:

- Solo pueden usarlo superusuarios, administradores maestros autorizados,
  administradores de empresa y gerentes de la empresa del pedido.
- Solo se cancelan pedidos cuyo `estado_pago` siga en `pendiente`.
- Los pedidos pagados o con pagos aprobados reciben `400 Bad Request`.
- Solo los intentos que continuan en `pendiente` cambian a `cancelado`.
- Los intentos rechazados se conservan como historial.
- La operacion no descuenta ni repone inventario.
- Repetir la solicitud devuelve `200 OK`, `duplicado=true` y la misma auditoria.

## 3. Cambios de interfaz recomendados

En el listado de pedidos:

- Mostrar `Cancelar pendiente` solo cuando `estado_pago === "pendiente"`.
- Solicitar un motivo obligatorio antes de enviar la accion.
- Bloquear el boton mientras la solicitud esta en curso.
- Tratar `duplicado=false` y `duplicado=true` como respuestas exitosas.
- Tras el exito, refrescar el pedido, el listado de pagos y el resumen comercial.
- Mostrar el estado `cancelado` como estado final, sin acciones de confirmacion.
- Mostrar motivo, administrador y fecha cuando exista auditoria de cancelacion.

Manejo de errores:

| HTTP | Accion del frontend |
| --- | --- |
| `400` | Refrescar el pedido y mostrar que ya no puede cancelarse |
| `401` | Ejecutar el flujo normal de renovacion de sesion |
| `403` | Mostrar falta de permisos sin revelar datos de otra empresa |
| `404` | Retirar el pedido de la vista actual o volver a cargar el listado |

## 4. Confirmacion presencial existente

La cancelacion no reemplaza la confirmacion. La unica accion administrativa
para aprobar un pago en sucursal continua siendo:

```http
POST /api/v1/pagos/{referencia}/confirmar-en-sucursal/
Authorization: Bearer ACCESS_TOKEN
```

No agregar otra forma de marcar pedidos o pagos como pagados desde el frontend.

## 5. Campos confirmados en listados

```http
GET /api/v1/pedidos/pedidos/
```

Cada pedido incluye:

- `estado_pago`
- `metodo_pago`
- `motivo_cancelacion`
- `cancelado_por`
- `cancelado_por_email`
- `fecha_cancelacion`

```http
GET /api/v1/pagos/
```

Cada pago incluye, entre otros:

- `metodo`
- `estado`
- `referencia`
- `pedido`
- `monto`

El nuevo valor posible de `Pago.estado` es `cancelado`.

## 6. Despliegue pendiente

Antes de probar estos cambios contra Render se debe:

1. Crear commit y push del backend.
2. Aplicar las migraciones `pedidos.0015` y `pagos.0003`.
3. Esperar que Render complete el despliegue.
4. Actualizar pedidos, pagos y resumen desde el frontend.

Verificacion local del backend: 207 pruebas aprobadas.
