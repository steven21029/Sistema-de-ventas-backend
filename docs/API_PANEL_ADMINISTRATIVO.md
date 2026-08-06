# Contrato API del panel administrativo

Estado: implementado en backend Django y verificado el 6 de agosto de 2026.

Este documento es el contrato oficial para implementar el panel React. Las
rutas publicas existentes se conservan. Todas las rutas indicadas empiezan con
la base del backend, por ejemplo `http://127.0.0.1:8000/api/`.

## 1. Autenticacion

Login:

```http
POST /api/usuarios/login/
Content-Type: application/json
```

```json
{
  "email": "analizahn2025@gmail.com",
  "password": "0000"
}
```

La respuesta entrega `access`. El refresh queda en una cookie `HttpOnly` y no
debe guardarse ni leerse desde JavaScript. En login, refresh y logout usar
`credentials: "include"`.

En las rutas protegidas enviar:

```http
Authorization: Bearer ACCESS_TOKEN
```

La sesion tiene un maximo absoluto de 5 horas. El access dura 15 minutos y se
renueva con `POST /api/usuarios/token/refresh/`. El logout usa
`POST /api/usuarios/token/logout/`.

## 2. Contexto multiempresa

Al entrar al panel consultar:

```http
GET /api/empresas/contexto-administrativo/?empresa_slug=analiza
```

La respuesta incluye `usuario`, `perfil`, `empresa_actual`,
`empresas_disponibles` y `permisos`.

La empresa tambien puede resolverse con:

```http
X-Frontend-Host: analiza.localhost
```

Reglas:

- Superusuario: puede seleccionar cualquier empresa activa.
- Administrador maestro: solo puede seleccionar sus `empresas_permitidas`.
- Administrador de empresa y gerente: siempre quedan limitados a su empresa.
- Comprador: no puede entrar a las APIs administrativas.
- En desarrollo local usar `?empresa_slug=analiza`.
- En produccion preferir dominio/subdominio y `X-Frontend-Host`.
- El backend no confia en `empresa` o `empresa_id` enviados por un admin de
  empresa o gerente; fuerza la empresa de su sesion.
- Solicitar expresamente otra empresa responde `403 Forbidden`.

## 3. Roles

| Rol | Alcance |
| --- | --- |
| Superusuario Django | Todas las empresas, crea empresas y administradores maestros |
| `administrador_maestro` | Empresas asignadas en `empresas_permitidas` |
| `administrador_empresa` | Su empresa; crea gerentes/compradores si tiene permiso |
| `gerente` | Su empresa; crea compradores solo si `puede_crear_usuarios=true` |
| `comprador` | Tienda, perfil, carrito, pedidos y pagos propios |

## 4. Convenciones de listas

Filtros comunes cuando la ruta los admite:

- `empresa_slug=analiza`
- `buscar=texto`
- `orden=campo` o `orden=-campo`
- `incluir_inactivos=true`
- `paginar=true`
- `page=1`
- `tamano_pagina=20`, maximo `100`

Respuesta paginada:

```json
{
  "count": 25,
  "next": "...page=2",
  "previous": null,
  "results": []
}
```

Menu, sucursales administrativas, catalogo administrativo, paquetes y
usuarios siempre se paginan. Promociones, contactos, pedidos y pagos conservan
la lista anterior salvo que se envie `paginar=true`.

## 5. Empresa y navegacion

| Metodo | Ruta | Uso |
| --- | --- | --- |
| `GET` | `/api/empresas/contexto-administrativo/` | Usuario, empresa y permisos actuales |
| `GET`, `PATCH` | `/api/empresas/mi-empresa/` | Branding y configuracion de la empresa actual |
| `GET` | `/api/empresas/items-menu/` | Listar modulos oficiales del menu |
| `GET`, `PUT`, `PATCH` | `/api/empresas/items-menu/{id}/` | Cambiar texto, orden o estado |
| CRUD | `/api/empresas/sucursales/` | Sucursales |
| CRUD | `/api/empresas/` | Solo superusuario; crear y administrar empresas |
| `GET` | `/api/empresas/sobre-nosotros/` | Contenido publico por empresa |
| `GET`, `PATCH` | `/api/empresas/mi-sobre-nosotros/` | Administrar contenido de la empresa actual |

`mi-empresa` permite cambiar nombre, logo, imagen general de sucursales,
colores, telefono, correo, direccion, sitio web, redes sociales, envios,
impuesto e imagenes de productos. `slug`, dominio, subdominio, modo de
inventario y estado activo son de solo lectura en esta ruta y los controla el
superusuario.

Campos editables de redes sociales:

```json
{
  "instagram_url": "https://www.instagram.com/analiza",
  "whatsapp_url": "https://wa.me/50499999999",
  "facebook_url": "https://www.facebook.com/analiza",
  "tiktok_url": "https://www.tiktok.com/@analiza"
}
```

Todos son opcionales, deben usar HTTPS y pertenecer al dominio oficial de la
red correspondiente. No existen endpoints separados para redes sociales.

Item de menu:

```json
{
  "clave": "servicios",
  "texto": "Servicios medicos",
  "ruta": "/servicios",
  "orden": 4,
  "activo": true,
  "abre_en_nueva_pestana": false
}
```

Los modulos oficiales son `inicio`, `examenes`, `perfiles`, `servicios`,
`promociones`, `sucursales`, `contacto` y `sobre_nosotros`. Todas las empresas
reciben los ocho automaticamente. `clave`, `ruta` y
`abre_en_nueva_pestana` son de solo lectura; solo pueden cambiarse `texto`,
`orden` y `activo`. No existe `POST` ni `DELETE` para items del menu.

Rutas oficiales:

```text
inicio             /
examenes           /examenes
perfiles           /perfiles
servicios          /servicios
promociones        /promociones
sucursales         /sucursales
contacto           /contacto
sobre_nosotros     /sobre-nosotros
```

Contenido publico de Sobre nosotros:

```http
GET /api/empresas/sobre-nosotros/?empresa_slug=analiza
```

Devuelve `titulo`, `introduccion`, `historia`, `mision`, `vision`,
`valores_lista`, `compromiso` e `imagen_final`. Si el modulo
`sobre_nosotros` esta inactivo, la API publica responde `404`. El panel edita
la ficha fija mediante `GET/PATCH /api/empresas/mi-sobre-nosotros/`. No se
crean paginas ni secciones genericas.

## 6. Catalogo

| Recurso | Ruta CRUD |
| --- | --- |
| Familias | `/api/catalogo/familias/` |
| Categorias | `/api/catalogo/categorias/` |
| Productos/servicios | `/api/catalogo/productos/` |
| Perfiles/combos | `/api/catalogo/paquetes/` |

Filtros: `buscar`, `familia`, `categoria`, `agotado`, `orden` e
`incluir_inactivos`. Paquetes tambien acepta `tipo=perfil|combo`.

Los productos administrativos devuelven `id`, pero el ID sigue oculto en los
flujos publicos que usan `codigo`. `existencia` es de solo lectura y comienza
en cero. Los ajustes se realizan por las APIs de inventario, nunca mediante
`PATCH` del producto.

Ejemplo de paquete:

```json
{
  "tipo": "perfil",
  "codigo": "PERFIL-001",
  "nombre": "Perfil basico",
  "descripcion": "",
  "precio_normal": "1200.00",
  "precio": "995.00",
  "porcentaje_descuento": 17,
  "activo": true,
  "orden": 1,
  "productos": [
    {"producto_id": 10, "cantidad": 1, "orden": 1},
    {"producto_id": 12, "cantidad": 2, "orden": 2}
  ]
}
```

Todos los componentes deben pertenecer a la empresa actual. La cantidad se
usa para validar y descontar inventario cuando corresponda.

## 7. Promociones

| Recurso | Ruta CRUD |
| --- | --- |
| Banners del carrusel | `/api/promociones/banners/` |
| Ofertas de la pagina Promociones | `/api/promociones/ofertas/` |
| Descuentos del carrito | `/api/promociones/descuentos/` |

Los tres recursos son independientes. Un banner no se convierte en oferta ni
en descuento. Para administrar registros apagados usar
`incluir_inactivos=true`; para paginar agregar `paginar=true`.

Las ofertas usan `tipo=producto|productos|paquete` y reciben `productos_ids` o
`paquete` segun su tipo. Los descuentos solo aplican a productos simples y
reciben `alcance=todos|seleccionados|individual` con `productos_ids`.

## 8. Usuarios

| Metodo | Ruta | Uso |
| --- | --- | --- |
| `GET`, `POST` | `/api/usuarios/administracion/` | Listar y crear |
| `GET`, `PUT`, `PATCH` | `/api/usuarios/administracion/{id}/` | Consultar o actualizar |
| `POST` | `/api/usuarios/administracion/{id}/bloquear/` | Bloquear e invalidar sesiones |
| `POST` | `/api/usuarios/administracion/{id}/desbloquear/` | Reactivar cuenta verificada |

Filtros: `buscar`, `rol`, `activo`, `orden`, `empresa_slug`, `page` y
`tamano_pagina`.

Creacion:

```json
{
  "username": "gerente-analiza",
  "email": "gerente@example.com",
  "first_name": "Nombre",
  "last_name": "Apellido",
  "password": "ClaveSegura123!",
  "rol": "gerente",
  "telefono": "9999-9999",
  "numero_identidad": "0801199912345",
  "correo_verificado": true,
  "puede_crear_usuarios": false,
  "activo": true
}
```

La contrasena nunca se devuelve. `numero_identidad` acepta exactamente 13
digitos y es unico por empresa. Cambiar la contrasena o bloquear la cuenta
revoca todos sus refresh tokens. Una cuenta solo se activa si el correo esta
verificado. No existe `DELETE` de usuarios.

## 9. Contactos, pedidos y pagos

Contactos:

- `POST /api/contacto/mensajes/` sigue siendo publico.
- `GET /api/contacto/mensajes/` es la bandeja administrativa.
- `GET`, `PUT`, `PATCH /api/contacto/mensajes/{id}/` permite cambiar solo
  `estado`.
- Filtros: `buscar`, `estado`, `fecha_desde`, `fecha_hasta`, `orden`.

Pedidos:

- `GET /api/pedidos/pedidos/`
- `GET /api/pedidos/pedidos/{id}/`
- `GET /api/pedidos/detalles/`
- `GET /api/pedidos/pedidos/{id}/prefactura/`
- Filtros: `buscar`, `cliente`, `estado` o `estado_pago`, `fecha_desde`,
  `fecha_hasta`, `orden`.

Pagos:

- `GET /api/pagos/`
- `GET /api/pagos/{referencia}/`
- `POST /api/pagos/iniciar/` solo inicia o recupera el pago pendiente del
  pedido del comprador.
- Filtros: `buscar`, `cliente`, `estado`, `proveedor`, `fecha_desde`,
  `fecha_hasta`, `orden`.

Pedidos y pagos son fotografias historicas de solo lectura. Sus estados de
pago solo cambian mediante el flujo controlado y webhook firmado. El backend
ya evita dos pagos pendientes para el mismo pedido y procesa webhooks de forma
idempotente.

## 10. Imagenes

Para subir archivo usar `multipart/form-data`. Para almacenamiento externo
usar el campo `imagen_url` cuando exista. La respuesta normaliza la imagen a
`imagen_final`, dando prioridad a la URL externa.

No enviar manualmente `Content-Type` al usar `FormData`; el navegador agrega
el boundary. Para quitar una imagen local enviar el campo vacio o `null` segun
el control React y limpiar tambien `imagen_url` si no se desea respaldo.

## 11. Errores

| Estado | Significado |
| --- | --- |
| `400` | Validacion de campos o relacion invalida |
| `401` | Token ausente, vencido o bloqueado |
| `403` | Rol insuficiente o empresa no permitida |
| `404` | Registro inexistente dentro del alcance permitido |
| `409` | Eliminacion bloqueada por historial relacionado |

El frontend debe mostrar los mensajes por campo cuando la respuesta sea un
objeto, y `detail` o `detalle` cuando sea un error general.

## 12. Desactivar o eliminar

Preferir siempre `PATCH {"activo": false}` o `PATCH {"activa": false}`.

- Empresa, menu, sucursal, familia, categoria, producto, paquete, banner,
  oferta y descuento pueden desactivarse.
- Usuarios se bloquean con la accion `bloquear`.
- Contactos cambian de estado y no se eliminan.
- Pedidos, detalles, pagos y eventos webhook nunca se eliminan.
- `DELETE` se acepta solamente en recursos sin historia dependiente.
- Si existe historia protegida, la API responde `409` y debe ofrecerse
  desactivar en la interfaz.

## 13. Secuencia recomendada para React

1. Hacer login y guardar `access` solo en memoria.
2. Consultar `contexto-administrativo`.
3. Si hay varias empresas, seleccionar una de `empresas_disponibles`.
4. Enviar el slug o `X-Frontend-Host` en cada consulta administrativa.
5. Construir el menu lateral segun rol y permisos devueltos.
6. Consumir listas paginadas y conservar filtros en la URL de React.
7. En formularios, no permitir elegir empresa a admins de empresa/gerentes.
8. Ante `401`, intentar refresh una vez; si falla, volver al login.
9. Ante `403`, cerrar la vista solicitada sin mostrar datos parciales.
10. Ante `409`, ofrecer desactivar el registro.

## 14. Reportes comerciales

El panel debe consumir los calculos oficiales del backend mediante:

- `GET /api/v1/reportes/resumen-ventas/`
- `GET /api/v1/reportes/ventas/exportar/`

Ambas rutas tambien conservan compatibilidad bajo `/api/`. Solo pueden usarlas
superusuarios, administradores maestros autorizados, administradores de empresa
y gerentes de la empresa solicitada. Los compradores reciben `403`.

El contrato completo, las reglas contables, los parametros y los formatos de
descarga estan documentados en `docs/API_REPORTES_COMERCIALES.md`.

## 15. Pago en sucursal

El pago en linea existente conserva su contrato:

- `POST /api/v1/pagos/iniciar/`

El comprador puede elegir una sucursal activa de la empresa y generar su
prefactura mediante:

- `POST /api/v1/pedidos/pedidos/{pedido_id}/pago-en-sucursal/`
- `GET /api/v1/pedidos/pedidos/{pedido_id}/prefactura/pdf/`
- `POST /api/v1/pedidos/pedidos/{pedido_id}/prefactura/reenviar-correo/`

La confirmacion presencial es administrativa:

- `POST /api/v1/pagos/{referencia}/confirmar-en-sucursal/`

Todas las rutas tambien funcionan bajo `/api/`. El inicio es idempotente, no
descuenta inventario y envia el PDF solamente al correo verificado del
comprador. La confirmacion valida inventario y reutiliza los efectos
comerciales del pago aprobado, sin duplicarlos si se repite.

El contrato completo, las respuestas, permisos, errores y variables de
entorno estan documentados en `docs/API_PAGO_EN_SUCURSAL.md`.
