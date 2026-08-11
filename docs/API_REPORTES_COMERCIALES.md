# Contrato API de reportes comerciales

Estado: implementado y verificado el 11 de agosto de 2026.

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
GET /api/v1/reportes/resumen-ventas/?empresa_slug=analiza&fecha_desde=2026-08-01&fecha_hasta=2026-08-31&agrupacion=mes&comparar_periodo_anterior=true&sucursal_id=5
```

Parametros:

| Parametro | Tipo | Regla |
| --- | --- | --- |
| `empresa_slug` | slug | Obligatorio |
| `fecha_desde` | `YYYY-MM-DD` | Obligatorio e inclusivo |
| `fecha_hasta` | `YYYY-MM-DD` | Obligatorio e inclusivo |
| `agrupacion` | `dia` o `mes` | Opcional; por defecto `dia` |
| `comparar_periodo_anterior` | booleano | Opcional; por defecto `false` |
| `ciudad` | texto | Opcional; coincidencia exacta sin distinguir mayusculas |
| `sucursal_id` | entero | Opcional; debe pertenecer a la empresa |
| `examen_id` | entero | Opcional; es el `id` de un producto de la empresa |
| `familia_id` | entero | Opcional; debe pertenecer a la empresa |

Los cuatro filtros son combinables. Si se envian `examen_id` y `familia_id`,
el examen debe pertenecer a la familia seleccionada.

Respuesta:

```json
{
  "periodo": {
    "fecha_desde": "2026-08-01",
    "fecha_hasta": "2026-08-31"
  },
  "filtros_aplicados": {
    "ciudad": null,
    "sucursal_id": 5,
    "examen_id": null,
    "familia_id": null
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

## Filtros segmentados

Los filtros se aplican antes de calcular ingresos, estados, pendientes,
metodos de pago, series y productos mas vendidos. Tambien se aplican al
periodo anterior cuando se solicita comparacion.

- `ciudad` incluye pedidos cuyo `municipio_entrega` coincide con la ciudad o
  cuyo pago en sucursal apunta a una `SucursalEmpresa.ciudad` coincidente.
- `sucursal_id` incluye pedidos que seleccionaron esa sucursal para pagar.
- `examen_id` incluye pedidos con ese producto directo o dentro de un perfil o
  combo. El ranking de productos se limita a las lineas coincidentes.
- `familia_id` incluye pedidos con productos de esa familia, directamente o
  dentro de un perfil o combo.
- Los IDs ajenos a la empresa autorizada devuelven `400 Bad Request` y nunca
  permiten consultar informacion de otra empresa.
- `filtros_aplicados` siempre devuelve las cuatro claves. Los filtros que no
  fueron enviados aparecen como `null`.

## Descarga de reportes

```http
GET /api/v1/reportes/ventas/exportar/?empresa_slug=analiza&fecha_desde=2026-08-01&fecha_hasta=2026-08-31&formato=xlsx&tipo=sucursales&ciudad=Tegucigalpa
```

Parametros:

| Parametro | Valores |
| --- | --- |
| `empresa_slug` | Slug obligatorio |
| `fecha_desde` | `YYYY-MM-DD`, inclusivo |
| `fecha_hasta` | `YYYY-MM-DD`, inclusivo |
| `formato` | `xlsx` o `pdf` |
| `tipo` | `resumen`, `ventas`, `pagos`, `impuestos`, `sucursales` o `familias` |
| `ciudad` | Opcional; misma regla del resumen |
| `sucursal_id` | Opcional; misma regla del resumen |
| `examen_id` | Opcional; misma regla del resumen |
| `familia_id` | Opcional; misma regla del resumen |

Contenido por tipo:

- `resumen`: totales superiores y productos mas vendidos. Los estados no se
  repiten en el detalle exportado.
- `ventas`: pedidos, cliente, estado y fotografia completa de montos.
- `pagos`: intentos de pago, proveedor, estado, referencia y confirmacion.
- `impuestos`: pedidos confirmados, base imponible, tasa e impuesto historico.
- `sucursales`: ranking de sucursales elegidas para pago presencial, ordenado
  por personas unicas y luego por cantidad de selecciones.
- `familias`: detalle individual de todos los productos o examenes de las
  familias incluidas. Muestra codigo, estado del catalogo, pedidos, unidades e
  ingresos directos. Los elementos sin ventas tambien aparecen con valores
  cero. Al enviar `familia_id`, solamente se listan los elementos de esa
  familia; no se devuelve una unica fila resumida.

### Reporte de sucursales

Este reporte mide intencion de visita desde la pagina. Una seleccion es un
pedido con `metodo_pago=sucursal` y `sucursal_pago` registrada dentro del
periodo. No confirma que la persona haya llegado fisicamente.

Columnas:

- `Ciudad` y `Sucursal`.
- `Personas`: compradores unicos que eligieron la sucursal.
- `Selecciones`: cantidad de pedidos que eligieron la sucursal.
- `Pagados`, `Pendientes` y `Otros` para separar el resultado comercial.
- `Monto`: suma historica de los pedidos seleccionados, sin usarla como ingreso
  confirmado.

Un comprador con varios pedidos en la misma sucursal cuenta una sola vez en
`Personas`, pero cada pedido cuenta en `Selecciones`. El aislamiento por
empresa, el periodo y todos los filtros segmentados se conservan.

Todos los archivos incluyen empresa, periodo, totales y detalle. No incluyen el
slug ni la moneda.
Los nombres siguen este formato:

```text
reporte_{tipo}_{fecha_desde}_{fecha_hasta}.{formato}
```

Content types:

| Formato | `Content-Type` |
| --- | --- |
| XLSX | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` |
| PDF | `application/pdf` |

La respuesta incluye `Content-Disposition: attachment` con el nombre final.

### Diseno de los reportes PDF

Los seis tipos de PDF comparten la identidad visual de la prefactura, sin
marca de agua:

- Formato A4 horizontal para conservar la legibilidad de tablas extensas.
- Logo, nombre, colores, telefono, correo, direccion y sitio web tomados de la
  empresa consultada.
- Encabezado de reporte comercial, titulo, periodo y fecha de generacion en
  `America/Tegucigalpa`.
- Resumen de totales oficiales y detalle correspondiente al tipo solicitado.
- Encabezado de columnas repetido y filas indivisibles en varias paginas.
- Pie con contacto de la empresa y numero de pagina.

No cambia el endpoint, los parametros, el `Content-Type` ni el nombre de
archivo. El frontend debe continuar procesando la respuesta como `blob`.

`empresa_slug` se conserva exclusivamente como parametro obligatorio para
seleccionar y autorizar la empresa. No se devuelve como dato del reporte. La
moneda tampoco se devuelve en JSON ni se incluye en XLSX o PDF.

### Diseno de los reportes Excel

Los seis tipos de Excel comparten la identidad visual del PDF:

- Logo, nombre, colores y contacto dinamicos de la empresa.
- Bloques separados para datos del reporte, totales y detalle.
- Valores monetarios y cantidades guardados como numeros con formato de Excel.
- Encabezados, bordes, filas alternas, autofiltro y panel congelado.
- Impresion A4 horizontal, ajuste a una pagina de ancho y pie paginado.
- Sin `empresa_slug`, moneda ni filas repetidas de estados en el resumen.

El formato `csv` fue retirado. Enviar `formato=csv` devuelve `400 Bad Request`.

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
- Enviar los filtros opcionales sin cambiar de endpoint. No enviar una cadena
  vacia como ID.
- Para comparar sucursales usar `tipo=sucursales`; para comparar familias usar
  `tipo=familias`. Ambos aceptan `formato=xlsx` y `formato=pdf`.
- Al seleccionar una familia, recargar el selector de examenes mediante
  `GET /api/v1/catalogo/examenes/?empresa_slug=analiza&familia={familia_id}`.
  La opcion de examen debe reiniciarse cuando cambie la familia.

Fuentes sugeridas para los controles del panel:

- `GET /api/v1/empresas/sucursales/?empresa_slug=analiza` devuelve `id`,
  `nombre` y el nuevo campo `ciudad`. El frontend puede obtener de ahi la lista
  unica de ciudades de sucursales.
- `GET /api/v1/catalogo/examenes/?empresa_slug=analiza` devuelve los examenes;
  enviar su `id` como `examen_id`.
- `GET /api/v1/catalogo/familias/?empresa_slug=analiza` devuelve las familias;
  enviar su `id` como `familia_id`.

La API de sucursales tambien acepta `ciudad=Tegucigalpa`, permite buscar por
ciudad con `buscar` y admite `orden=ciudad` o `orden=-ciudad`.

La forma de la respuesta de sucursales depende del contexto actual:

- Sin token administrativo es un arreglo directo: `[{...}]`.
- Con token administrativo usa paginacion: `{"count": 2, "results": [{...}]}`.

El frontend debe normalizarla antes de construir ambos selectores:

```javascript
const sucursales = Array.isArray(data) ? data : (data.results ?? []);
const ciudades = [...new Set(
  sucursales.map((sucursal) => sucursal.ciudad).filter(Boolean),
)];
```

La ausencia temporal de ciudades no debe impedir mostrar las sucursales. El
campo puede estar vacio en registros creados antes de la migracion `0017`.

Campos relacionados ya disponibles:

- `GET /api/v1/pedidos/pedidos/` incluye `metodo_pago` en cada pedido.
- `GET /api/v1/pagos/` incluye `metodo` en cada pago.
