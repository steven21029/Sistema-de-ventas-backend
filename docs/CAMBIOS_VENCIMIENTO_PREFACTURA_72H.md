# Vencimiento de prefacturas para pago en sucursal

## Regla oficial

- Vigencia: 72 horas desde `fecha_prefactura`.
- Durante la vigencia se respetan los montos guardados en el pedido.
- Al vencer, `pedido.estado_pago` pasa a `rechazado`.
- Los pagos pendientes relacionados pasan a `rechazado` con
  `codigo_respuesta=PREFACTURA_VENCIDA`.
- No se descuenta inventario.
- El pago en linea no cambia.

## Respuesta al iniciar pago en sucursal

`POST /api/v1/pedidos/pedidos/{id}/pago-en-sucursal/` agrega:

```json
{
  "prefactura": {
    "fecha_vencimiento": "2026-08-16T10:30:00-06:00",
    "vigencia_horas": 72,
    "vigente": true,
    "mensaje_vigencia": "Esta prefactura estara disponible durante 72 horas..."
  }
}
```

`GET /api/v1/pedidos/pedidos/` agrega a cada pedido:

```json
{
  "prefactura_fecha_vencimiento": "2026-08-16T10:30:00-06:00",
  "prefactura_vigente": true,
  "mensaje_vigencia_prefactura": "Esta prefactura estara disponible durante 72 horas..."
}
```

`GET /api/v1/pedidos/pedidos/{id}/prefactura/` agrega `vigente`,
`vigencia_horas` y `mensaje_vigencia`.

## Comportamiento para el frontend

Mostrar el mensaje enviado por el backend y la fecha de vencimiento. No
recalcular el plazo oficial ni modificar los totales. Cuando
`estado_pago=rechazado` o `prefactura_vigente=false`, deshabilitar confirmacion
y reenvio, informar que el plazo finalizo y dirigir al comprador a generar una
nueva compra.

La descarga del PDF se conserva como historial. La confirmacion y el reenvio
de una prefactura vencida responden `400` con la clave `prefactura`.

## Operacion

Aplicar la migracion:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
```

Ejecutar periodicamente, cada 5 o 10 minutos:

```powershell
.\.venv\Scripts\python.exe manage.py vencer_prefacturas_sucursal
```

En Render, configurar `PREFACTURA_VIGENCIA_HORAS=72` y crear una tarea
programada con ese comando. Las consultas y acciones relacionadas tambien
procesan vencimientos de forma inmediata.
