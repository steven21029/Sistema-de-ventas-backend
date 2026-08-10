# Contrato API de reportes comerciales

Estado: implementado y verificado el 10 de agosto de 2026.

Las rutas estan disponibles con las bases `/api/` y `/api/v1/`. El frontend
debe preferir `/api/v1/`.

## Autorizacion y empresa

Todas las solicitudes requieren:

```http
Authorization: Bearer ACCESS_TOKEN
```

Pueden consultar reportes:

- Superusuario Django.
- `administrador_maestro`, solo para sus empresas permitidas.
- `administrador_empresa`, solo para su empresa.
- `gerente`, solo para su empresa.

Un comprador o un usuario que solicita otra empresa recibe `403 Forbidden`.
`empresa_slug` siempre es obligatorio y no sustituye la autorizacion del
usuario.

## Resumen comercial

```http
GET /api/v1/reportes/resumen-ventas/?empresa_slug=analiza&fecha_desde=2026-08-01&fecha_hasta=2026-08-31&agrupacion=mes&comparar_periodo_anterior=true
```

Parametros:

| Parametro | Tipo | Regla |
| --- | --- | --- |
| `empresa_slug` | slug | Obligatorio |
| `fecha_desde` | `YYYY-MM-DD` | Obligatorio e inclusivo |
| `fecha_hasta` | `YYYY-MM-DD` | Obligatorio e inclusivo |
| `agrupacion` | `dia` o `mes` | Opcional; por defecto `dia` |
| `comparar_periodo_anterior` | booleano | Opcional; por defecto `false` |

Respuesta:

```json
{
  "empresa_slug": "analiza",
  "moneda": "HNL",
  "periodo": {
    "fecha_desde": "2026-08-01",
    "fecha_hasta": "2026-08-31"
  },
  "resumen": {
    "ingresos_confirmados": "25000.00",
    "ventas_confirmadas": 32,
    "ticket_promedio": "781.25",
    "subtotal": "23000.00",
    "descuentos": "1200.00",
    "impuestos": "2500.00",
    "envios": "700.00",
    "monto_pendiente": "3500.00",
    "pedidos_pendientes": 5,
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
    },
    "variacion_ingresos_porcentaje": 12.5,
    "variacion_ventas_porcentaje": 8.2
  },
  "serie": [
    {
      "periodo": "2026-08",
      "etiqueta": "Ago",
      "ingresos": "25000.00",
      "ventas": 32
    }
  ],
  "estados": [
    {"estado": "pagado", "cantidad": 32, "monto": "25000.00"},
    {"estado": "pendiente", "cantidad": 5, "monto": "3500.00"}
  ],
  "productos_mas_vendidos": [
    {
      "codigo": "EXA-001",
      "nombre": "Hemograma",
      "cantidad": 18,
      "ingresos": "5400.00"
    }
  ]
}
```

## Reglas de calculo

- El periodo se aplica a `Pedido.fecha_creacion` en la zona horaria
  `America/Tegucigalpa`, desde las `00:00:00` de `fecha_desde` hasta antes de
  las `00:00:00` del dia posterior a `fecha_hasta`.
- Un pedido cuenta como confirmado si tiene `estado_pago=pagado` o al menos un
  pago con `estado=aprobado`.
- Los totales confirmados usan exclusivamente la fotografia historica del
  pedido: `subtotal`, `descuento_total`, `impuesto`, `envio` y `total`.
- `ticket_promedio` es ingresos confirmados entre ventas confirmadas.
- `pagos_por_metodo` usa exclusivamente pagos con `estado=aprobado` y el
  valor historico de `Pago.metodo`. Cada pedido se cuenta y suma una sola vez,
  aunque existan varios intentos. Siempre contiene `sucursal` y `en_linea`, con
  cantidad cero y monto `"0.00"` cuando no hay pagos confirmados.
- `pendientes_por_metodo` incluye pedidos cuyo `estado_pago` oficial sigue en
  `pendiente` y que no tienen ningun pago aprobado. Se agrupan por
  `Pedido.metodo_pago`; el valor `pendiente` de seleccion se informa como
  `sin_metodo`. Los intentos rechazados no duplican ni eliminan el pedido de
  este agregado. Las tres claves siempre estan presentes y usan `Pedido.total`.
- Un pedido es pendiente si no esta pagado, no esta cancelado y no tiene un
  resultado final rechazado sin otro intento pendiente.
- Un intento rechazado no elimina la posibilidad de reintentar. Si existe
  tambien un pago pendiente, el pedido se informa como `pendiente`.
- `rechazado` y `cancelado` nunca participan en ingresos ni en monto pendiente.
- `productos_mas_vendidos` contiene hasta 10 lineas historicas confirmadas,
  ordenadas por cantidad. Sus ingresos son netos de descuento y no distribuyen
  impuesto ni envio entre productos.
- La serie incluye periodos sin ventas con valores cero.
- La comparacion usa el bloque inmediatamente anterior con la misma cantidad
  de dias calendario. Por ejemplo, el 1 al 31 de agosto se compara con el 1 al
  31 de julio.
- Si el periodo anterior no tiene ventas, la variacion correspondiente es
  `null`, porque no existe una base porcentual valida.
- Los montos siempre se entregan como cadenas con dos decimales. Las
  variaciones son numeros con un decimal o `null`.

## Descarga de reportes

```http
GET /api/v1/reportes/ventas/exportar/?empresa_slug=analiza&fecha_desde=2026-08-01&fecha_hasta=2026-08-31&formato=xlsx&tipo=ventas
```

Parametros:

| Parametro | Valores |
| --- | --- |
| `empresa_slug` | Slug obligatorio |
| `fecha_desde` | `YYYY-MM-DD`, inclusivo |
| `fecha_hasta` | `YYYY-MM-DD`, inclusivo |
| `formato` | `csv`, `xlsx` o `pdf` |
| `tipo` | `resumen`, `ventas`, `pagos` o `impuestos` |

Contenido por tipo:

- `resumen`: totales, desglose por estado y productos mas vendidos.
- `ventas`: pedidos, cliente, estado y fotografia completa de montos.
- `pagos`: intentos de pago, proveedor, estado, referencia y confirmacion.
- `impuestos`: pedidos confirmados, base imponible, tasa e impuesto historico.

Todos los archivos incluyen empresa, slug, periodo, moneda, totales y detalle.
Los nombres siguen este formato:

```text
reporte_{tipo}_{empresa_slug}_{fecha_desde}_{fecha_hasta}.{formato}
```

Content types:

| Formato | `Content-Type` |
| --- | --- |
| CSV | `text/csv; charset=utf-8` |
| XLSX | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` |
| PDF | `application/pdf` |

La respuesta incluye `Content-Disposition: attachment` con el nombre final.

## Integracion del frontend

- Sustituir los calculos locales del panel por el objeto `resumen`.
- Consumir `resumen.pagos_por_metodo` directamente para cantidades y montos
  confirmados por canal; no reconstruirlo a partir de intentos de pago.
- Consumir `resumen.pendientes_por_metodo` para los pedidos administrables que
  aun no tienen pago confirmado.
- Usar `serie` directamente para graficas; no volver a agrupar pedidos.
- Usar `estados` para distribucion de ventas y `productos_mas_vendidos` para el
  ranking.
- Tratar todos los montos como decimales, no como valores de punto flotante.
- Para descargar, solicitar el endpoint como `blob` y respetar el nombre de
  `Content-Disposition`.
- Mostrar `403` como falta de acceso a la empresa y `400` como error de filtros.

Campos relacionados ya disponibles:

- `GET /api/v1/pedidos/pedidos/` incluye `metodo_pago` en cada pedido.
- `GET /api/v1/pagos/` incluye `metodo` en cada pago.
