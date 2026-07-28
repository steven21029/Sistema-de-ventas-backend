# Brief para iniciar el frontend - Sistema web de ventas en linea

Fecha de preparacion: 2026-07-22

Este documento resume lo necesario para abrir una nueva conversacion y comenzar el frontend React. El backend queda pausado por ahora en este proyecto.

## 1. Objetivo del frontend

Construir una pagina web de ventas multiempresa. La primera empresa de referencia sera:

```text
Analiza Laboratorios Clinicos
```

Slug de empresa:

```text
Analiza
```

La pagina debe cargar primero como tienda/catalogo. El usuario no debe iniciar sesion para ver productos. El login y registro son secundarios y deben aparecer cuando el cliente quiera pagar, entrar a su cuenta o consultar pedidos.

## 2. Estilo visual aprobado

La interfaz debe ser:

- sobria;
- formal;
- limpia;
- facil de entender;
- enfocada en ventas;
- con textos principalmente negros;
- usando colores corporativos solo como acentos.

Colores base de Analiza:

```text
Rojo oscuro: #d1393d
Rojo claro:  #e94a51
Azul:        #2d4b77
Gris:        #6e6f70
Negro texto: #000000
Fondo:       #ffffff
```

La primera vista debe sentirse como una tienda real, no como landing page de marketing.

## 3. Pantalla inicial esperada

La primera pantalla debe mostrar:

- encabezado con logo/nombre de Analiza;
- buscador superior;
- menu principal;
- acceso a favoritos;
- icono del carrito;
- acceso a cuenta en un solo lugar;
- banner de promocion;
- familias/categorias;
- productos destacados o catalogo inicial;
- botones para agregar al carrito.

Regla importante:

- El carrito debe estar oculto por defecto.
- Se abre como panel desplegable cuando el usuario haga clic.
- No debe haber una seccion de citas medicas.
- No duplicar "Mi cuenta" en diferentes zonas de la misma vista.

## 4. Stack sugerido

Frontend aprobado:

```text
React
```

Backend actual:

```text
Django + Django REST Framework
```

Autenticacion:

```text
JWT Bearer token
```

Base de datos actual:

```text
SQLite local
```

Base futura:

```text
Supabase PostgreSQL
```

## 5. URL base local esperada

Si el backend corre localmente con Django:

```text
http://127.0.0.1:8000/api/
```

Para multiempresa por subdominio, la API principal para detectar la empresa sera:

```text
GET /api/empresas/actual/?host=analiza.localhost:3000
```

En el frontend se puede enviar:

```js
window.location.host
```

Ejemplo:

```text
http://127.0.0.1:8000/api/empresas/actual/?host=analiza.localhost:3000
```

Mientras no haya dominios reales, tambien se puede probar con:

```text
analiza.localhost
analiza.test
```

El respaldo por slug sigue funcionando:

```text
GET /api/empresas/actual/?slug=Analiza
GET /api/empresas/publica/?slug=Analiza
```

Para endpoints protegidos usar:

```http
Authorization: Bearer ACCESS_TOKEN
```

## 6. Flujo publico de ventas

El cliente puede:

1. Entrar a la pagina.
2. Ver productos sin iniciar sesion.
3. Buscar o filtrar productos.
4. Agregar productos al carrito visual del frontend.
5. Al pagar, iniciar sesion o registrarse.
6. Verificar correo si es cuenta nueva.
7. Sincronizar el carrito visual con el carrito autenticado.
8. Pagar cuando la integracion de pago este lista.
9. Consultar prefactura si el pedido esta pagado.

## 7. Autenticacion implementada

### Registro de comprador

Endpoint:

```text
POST /api/usuarios/registro-comprador/
```

Payload:

```json
{
  "empresa_slug": "Analiza",
  "nombre_completo": "Juan Perez",
  "email": "juan@example.com",
  "telefono": "99999999",
  "numero_identidad": "0801199012345",
  "password": "ClaveSegura123!",
  "password_confirmacion": "ClaveSegura123!",
  "acepta_terminos": true,
  "acepta_privacidad": true
}
```

Reglas:

- La identidad hondurena debe tener exactamente 13 digitos.
- Solo acepta numeros.
- La misma identidad no puede repetirse dentro de la misma empresa.
- Al registrarse, el usuario queda inactivo hasta verificar correo.
- El backend genera un codigo de verificacion.
- Por ahora el correo sale por consola; Brevo queda preparado para despues.

### Verificar correo

Endpoint:

```text
POST /api/usuarios/verificar-correo/
```

Payload:

```json
{
  "email": "juan@example.com",
  "codigo": "123456"
}
```

Reglas:

- Codigo de 6 digitos.
- Vence en 15 minutos.
- Maximo 5 intentos.
- Al verificar, activa usuario y perfil.

### Reenviar codigo de verificacion

Endpoint:

```text
POST /api/usuarios/reenviar-verificacion/
```

Payload:

```json
{
  "email": "juan@example.com"
}
```

Regla:

- Solo permite reenviar despues de 1 minuto.

### Login

Endpoint:

```text
POST /api/usuarios/login/
```

Payload:

```json
{
  "email": "juan@example.com",
  "password": "ClaveSegura123!"
}
```

Respuesta esperada:

```json
{
  "access": "...",
  "refresh": "...",
  "usuario": {},
  "perfil": {}
}
```

Si el usuario no verifico correo, no puede iniciar sesion.

### Refrescar token

Endpoint:

```text
POST /api/usuarios/token/refresh/
```

Payload:

```json
{
  "refresh": "REFRESH_TOKEN"
}
```

### Verificar token

Endpoint:

```text
POST /api/usuarios/token/verify/
```

Payload:

```json
{
  "token": "ACCESS_TOKEN"
}
```

### Mi perfil

Endpoint protegido:

```text
GET /api/usuarios/perfiles/mi-perfil/
```

Headers:

```http
Authorization: Bearer ACCESS_TOKEN
```

### Recuperacion de contrasena

Solicitar codigo:

```text
POST /api/usuarios/solicitar-recuperacion-contrasena/
```

Payload:

```json
{
  "email": "juan@example.com"
}
```

Confirmar nueva contrasena:

```text
POST /api/usuarios/confirmar-recuperacion-contrasena/
```

Payload:

```json
{
  "email": "juan@example.com",
  "codigo": "123456",
  "password": "NuevaClave123!",
  "password_confirmacion": "NuevaClave123!"
}
```

## 8. Catalogo publico implementado

El catalogo puede leerse sin login usando `empresa_slug`.

Familias:

```text
GET /api/catalogo/familias/?empresa_slug=Analiza
```

Categorias:

```text
GET /api/catalogo/categorias/?empresa_slug=Analiza
```

Productos:

```text
GET /api/catalogo/productos/?empresa_slug=Analiza
```

Filtros disponibles:

```text
GET /api/catalogo/productos/?empresa_slug=Analiza&buscar=hemograma
GET /api/catalogo/productos/?empresa_slug=Analiza&familia=Laboratorio
GET /api/catalogo/productos/?empresa_slug=Analiza&categoria=Hematologia
GET /api/catalogo/productos/?empresa_slug=Analiza&agotado=false
GET /api/catalogo/productos/?empresa_slug=Analiza&orden=precio_asc
GET /api/catalogo/productos/?empresa_slug=Analiza&orden=precio_desc
GET /api/catalogo/productos/?empresa_slug=Analiza&orden=nombre
```

Reglas:

- Solo devuelve empresa activa.
- Solo devuelve familias/categorias/productos activos.
- Crear, editar o eliminar catalogo requiere login y permisos.
- El `id` interno del producto no se muestra al cliente.
- El codigo de barra es unico por empresa.
- Todo producto inicia con existencia `0` al crearse.
- La existencia se cambia desde inventario, no desde catalogo.
- Los productos pueden traer `existencia`, `existencia_minima`, `agotado`, `inventario_bajo` y `estado_inventario`.

Estados de inventario:

```text
agotado = existencia 0
bajo = existencia mayor que 0 y menor o igual a existencia_minima
ok = existencia suficiente
```

### Paginas dinamicas de catalogo

Inicio:

```text
GET /api/catalogo/combos-destacados/?empresa_slug=Analiza
GET /api/catalogo/productos-mas-vendidos/?empresa_slug=Analiza
```

Examenes:

```text
GET /api/catalogo/examenes/?empresa_slug=Analiza&buscar=texto
```

Perfiles:

```text
GET /api/catalogo/perfiles/?empresa_slug=Analiza&buscar=texto
```

Servicios:

```text
GET /api/catalogo/servicios/?empresa_slug=Analiza&buscar=texto
```

Detalle de una rama de servicio:

```text
GET /api/catalogo/servicios/detalle/?empresa_slug=Analiza&servicio=imagenes
GET /api/catalogo/servicios/detalle/?empresa_slug=Analiza&servicio=Examenes
```

Reglas:

- Todos requieren `empresa_slug`.
- Todos devuelven solo registros activos de empresas activas.
- No exponen IDs internos.
- Productos y paquetes devuelven `imagen_final`.
- Si hay `imagen_url`, `imagen_final` usa esa URL externa.
- Si no hay `imagen_url`, `imagen_final` usa la imagen local del backend.
- `servicios` usa familias activas como ramas grandes de servicio.
- En servicios: Familia = rama principal, Categoria = opcion interna, Producto = vendible.
- `/catalogo/servicios/` devuelve las ramas y un resumen de categorias.
- `/catalogo/servicios/detalle/` devuelve la rama con categorias y productos agrupados.
- `combos-destacados` devuelve paquetes tipo combo con `destacado=true`.
- `perfiles` devuelve paquetes tipo perfil con productos internos.

## 9. Empresa publica implementada

Endpoint recomendado para la empresa actual:

```text
GET /api/empresas/actual/?host=analiza.localhost:3000
```

Respaldo por slug:

```text
GET /api/empresas/publica/?slug=Analiza
```

Uso:

- cargar nombre de empresa;
- logo;
- imagen general de sucursales;
- slug;
- subdominio;
- dominio personalizado;
- colores;
- telefono;
- correo;
- direccion;
- sitio web;
- `tiene_envios`;
- `opciones_entrega_disponibles`.

Campos de imagen general de sucursales en empresa:

```text
imagen_sucursales_url
imagen_sucursales_final
```

Regla multiempresa:

- En produccion el frontend deberia resolver la empresa con `window.location.host`.
- En desarrollo se puede mandar `host=analiza.localhost:3000`.
- Si no hay host confiable, usar `slug=Analiza` como respaldo temporal.
- Cuando la empresa se resuelva, usar su `slug` para APIs que todavia pidan `empresa_slug`.

Sucursales:

```text
GET /api/empresas/sucursales/?empresa_slug=Analiza&buscar=texto
```

Campos:

```text
nombre
direccion
telefono
horario
google_maps_url
imagen_final
latitud
longitud
orden
```

El frontend debe usar:

- `imagen_final` para mostrar la imagen de la sucursal.
- `google_maps_url` como enlace hacia Google Maps.

Regla de imagen:

- Todas las sucursales pueden usar una sola imagen general configurada en la empresa.
- El frontend no debe escoger imagen por sucursal manualmente; debe usar `imagen_final`.
- Si la empresa tiene imagen general de sucursales, `imagen_final` devuelve esa misma imagen para todas.
- Si no hay ninguna imagen, `imagen_final` devuelve `null`.

## 10. Menu principal por empresa implementado

El menu principal ya no debe estar fijo en el frontend.

El backend devuelve el menu dentro de:

```text
GET /api/empresas/actual/?host=analiza.localhost:3000
```

Tambien existe endpoint solo para menu:

```text
GET /api/empresas/menu/?empresa_slug=Analiza
GET /api/empresas/menu/?host=analiza.localhost:3000
```

Ejemplo de respuesta:

```json
[
  {
    "clave": "inicio",
    "texto": "Inicio",
    "ruta": "/",
    "orden": 1,
    "activo": true,
    "abre_en_nueva_pestana": false
  },
  {
    "clave": "examenes",
    "texto": "Examenes",
    "ruta": "/examenes",
    "orden": 2,
    "activo": true,
    "abre_en_nueva_pestana": false
  }
]
```

Reglas para frontend:

- Renderizar el menu usando `empresa.menu` o `/api/empresas/menu/`.
- Usar `texto` como nombre visible.
- Usar `ruta` para navegar.
- Ordenar por `orden` si el frontend necesita ordenar, aunque el backend ya lo devuelve ordenado.
- Si un item no viene en la respuesta, no debe mostrarse.
- No dejar nombres fijos como "Examenes" o "Servicios" en el componente.
- Si `abre_en_nueva_pestana = true`, abrir con target externo.

El menu predeterminado actual es:

```text
Inicio
Examenes
Perfiles
Servicios
Promociones
Sucursales
Contacto
```

Cada empresa puede cambiar esos textos desde el backend/admin.

## 11. Banner promocional implementado

Endpoint publico:

```text
GET /api/promociones/banners/?empresa_slug=Analiza
```

Uso:

- banner central;
- carrusel futuro;
- entrada visual hacia una pagina interna o externa.

Campos importantes para frontend:

```text
titulo
subtitulo
texto_boton
url_boton
imagen_final
texto_alternativo
orden
fecha_inicio
fecha_fin
```

Reglas:

- Cada banner pertenece a una empresa.
- El banner no es la pagina Promociones.
- El banner no debe listarse dentro de Promociones.
- El banner solo se muestra en carrusel y redirige usando `url_boton`.
- `url_boton` puede ser ruta interna como `/promociones/oferta-1` o URL externa.
- La API publica devuelve solo banners activos y vigentes.
- Si no hay banners activos, la respuesta debe ser `[]` y el frontend debe ocultar el espacio del banner.
- Aunque exista token de administrador guardado en el navegador, la llamada normal no devuelve banners inactivos.
- Para panel administrativo, usar `incluir_inactivos=true` si se necesita ver banners desactivados.
- La API publica no expone `id` interno ni `empresa` interna.
- El frontend debe usar `imagen_final`.
- Si existe `imagen_url`, `imagen_final` devuelve esa URL externa.
- Si no existe `imagen_url`, `imagen_final` devuelve la URL local de `imagen`.
- Esto deja listo el cambio futuro a almacenamiento externo sin romper el frontend.

Ejemplo de respuesta:

```json
[
  {
    "titulo": "Promocion especial",
    "subtitulo": "Disponible por tiempo limitado",
    "texto_boton": "Ver productos",
    "url_boton": "https://example.com/promocion",
    "imagen_final": "https://cdn.example.com/banner.jpg",
    "texto_alternativo": "Banner de promocion",
    "orden": 1
  }
]
```

Endpoint administrativo para ver tambien banners desactivados:

```text
GET /api/promociones/banners/?empresa_slug=Analiza&incluir_inactivos=true
```

## 12. Promociones y ofertas implementadas

La pagina Promociones debe consumir este endpoint:

```text
GET /api/promociones/ofertas/?empresa_slug=Analiza&buscar=texto
```

No debe consumir:

```text
GET /api/promociones/banners/
```

Tipos de oferta:

```text
producto = oferta de un producto individual
productos = oferta de varios productos juntos
paquete = oferta vinculada a combo o perfil
```

Ejemplo de respuesta:

```json
[
  {
    "tipo": "producto",
    "codigo": "OFERTA-001",
    "titulo": "Hemograma en oferta",
    "descripcion": "Precio especial por tiempo limitado.",
    "precio_normal": "150.00",
    "precio_oferta": "120.00",
    "porcentaje_descuento": 20,
    "imagen_final": "https://example.com/oferta.jpg",
    "url_destino": "/promociones/oferta-001",
    "paquete_resumen": null,
    "productos": [
      {
        "codigo_barra": "HEMO-001",
        "nombre": "Hemograma",
        "precio": "150.00"
      }
    ],
    "orden": 1
  }
]
```

Reglas:

- Las ofertas son independientes de los banners.
- Solo devuelve ofertas activas y vigentes.
- No expone IDs internos.
- Usa `imagen_final`.
- Si `url_destino` viene lleno, el frontend puede usarlo para abrir detalle o ruta interna.
- Los administradores pueden ver inactivas con `incluir_inactivos=true`.

## 13. Carrito y pedidos implementados

El carrito del backend requiere usuario autenticado.

Mi carrito:

```text
GET /api/pedidos/carritos/mi-carrito/
POST /api/pedidos/carritos/mi-carrito/
```

Este endpoint crea o devuelve el carrito activo del usuario autenticado.

Agregar producto al carrito sin exponer id interno:

```text
POST /api/pedidos/carritos/{id}/agregar-producto/
```

Payload:

```json
{
  "codigo_barra": "ABC123",
  "cantidad": 1
}
```

Respuesta:

- devuelve el carrito actualizado;
- los items incluyen codigo de barra, nombre, imagen, cantidad y precio;
- no devuelve el `id` interno del producto.

Carritos:

```text
GET /api/pedidos/carritos/
POST /api/pedidos/carritos/
```

Items de carrito:

```text
GET /api/pedidos/items-carrito/
POST /api/pedidos/items-carrito/
PATCH /api/pedidos/items-carrito/{id}/
DELETE /api/pedidos/items-carrito/{id}/
```

Generar pedido desde carrito:

```text
POST /api/pedidos/carritos/{id}/generar-pedido/
```

Payload:

```json
{
  "tipo_entrega": "retiro_en_local",
  "observaciones": ""
}
```

Para envio local o nacional:

```json
{
  "tipo_entrega": "envio_local",
  "nombre_recibe": "Juan Perez",
  "telefono_recibe": "99999999",
  "direccion_entrega": "Colonia Ejemplo, casa 123",
  "referencia_entrega": "Porton negro",
  "departamento_entrega": "Francisco Morazan",
  "municipio_entrega": "Tegucigalpa"
}
```

Pedidos:

```text
GET /api/pedidos/pedidos/
GET /api/pedidos/pedidos/{id}/
```

Prefactura:

```text
GET /api/pedidos/pedidos/{id}/prefactura/
```

## 14. Favoritos implementados

Favoritos requieren usuario autenticado.

Listar favoritos:

```text
GET /api/favoritos/?empresa_slug=Analiza
```

Agregar favorito sin exponer id interno del producto:

```text
POST /api/favoritos/
```

Payload:

```json
{
  "empresa_slug": "Analiza",
  "codigo_barra": "ABC123"
}
```

Eliminar favorito:

```text
DELETE /api/favoritos/{id}/
```

Reglas:

- No duplica el mismo producto como favorito para el mismo usuario y empresa.
- El producto debe estar activo.
- El producto se identifica por codigo de barra.

## 15. Inventario interno implementado

Estas rutas son para pantallas internas de administrador/gerente, no para la tienda publica.

Permisos:

- Administrador maestro puede ver todas las empresas o filtrar por `empresa_slug`.
- Administrador de empresa y gerente solo ven su empresa.
- Comprador no puede entrar a inventario.

Headers:

```http
Authorization: Bearer ACCESS_TOKEN
```

Listar todos los productos del inventario:

```text
GET /api/inventario/productos/
```

Filtros opcionales:

```text
GET /api/inventario/productos/?buscar=hemograma
GET /api/inventario/productos/?activo=true
GET /api/inventario/productos/?empresa_slug=Analiza
```

Resumen:

```text
GET /api/inventario/resumen/
```

Respuesta esperada:

```json
{
  "total_productos": 10,
  "productos_activos": 10,
  "productos_agotados": 2,
  "productos_bajo_stock": 3,
  "existencia_total": 120,
  "valor_inventario": "3500.00"
}
```

Productos agotados:

```text
GET /api/inventario/productos-agotados/
```

Productos con inventario bajo:

```text
GET /api/inventario/productos-bajo-stock/
```

Ajustar existencia por codigo de barra:

```text
POST /api/inventario/ajustar-existencia/
```

Payload:

```json
{
  "codigo_barra": "ABC123",
  "existencia_nueva": 10,
  "motivo": "Conteo fisico",
  "referencia": "AJ-001"
}
```

Para administrador maestro, si el codigo de barra existe en varias empresas, enviar tambien:

```json
{
  "empresa_slug": "Analiza",
  "codigo_barra": "ABC123",
  "existencia_nueva": 10
}
```

Historial de movimientos:

```text
GET /api/inventario/movimientos/
POST /api/inventario/movimientos/
```

Reglas:

- Un ajuste fija la existencia final contada.
- El ajuste puede ser `0`.
- Entrada y salida deben ser mayores que `0`.
- Cada ajuste crea historial en movimientos.
- El frontend debe identificar producto por `codigo_barra`, no por `id` interno.

## 16. Entrega

Regla por empresa:

- Si `tiene_envios = true`, se aceptan `envio_local` y `envio_nacional`.
- Si `tiene_envios = false`, solo se acepta `retiro_en_local`.

Para Analiza actualmente la configuracion local estaba como empresa sin envios, por lo que aplica:

```text
retiro_en_local
```

Direccion simple para envios:

- `nombre_recibe`
- `telefono_recibe`
- `direccion_entrega`
- `referencia_entrega`
- `departamento_entrega`
- `municipio_entrega`

Regla:

- Para `envio_local` y `envio_nacional`, la direccion simple es obligatoria.
- Para `retiro_en_local`, no es obligatoria.

Tarifas de entrega:

```text
GET /api/pedidos/tarifas-entrega/
```

Nota:

- Administrador maestro y administrador de empresa pueden cambiar tarifas.
- Compradores no administran tarifas.

## 17. Totales de pedido

Formula aprobada:

```text
base_imponible = subtotal - descuento_total
impuesto = base_imponible * 0.15
total = base_imponible + impuesto + envio
```

El envio se suma aparte y no forma parte de la base del impuesto.

Estados de pago actuales:

```text
pendiente
pagado
```

Cuando un pedido pasa a `pagado`:

- se descuenta inventario;
- se genera prefactura;
- no se descuenta inventario dos veces.

## 18. Prefactura

La prefactura existe como JSON, no como PDF todavia.

Incluye:

- empresa;
- cliente;
- numero de pedido;
- numero de prefactura;
- fecha;
- productos;
- cantidades;
- precios;
- subtotal;
- descuentos;
- impuesto 15%;
- envio;
- total;
- estado de pago;
- leyenda.

Leyenda obligatoria:

```text
Este documento corresponde a una prefactura y no representa una factura fiscal original.
```

### Formulario de contacto

Endpoint publico:

```text
POST /api/contacto/mensajes/
```

Payload:

```json
{
  "empresa_slug": "Analiza",
  "nombre": "Cliente",
  "telefono": "99999999",
  "correo": "cliente@example.com",
  "asunto": "Consulta",
  "mensaje": "Quiero informacion."
}
```

Reglas:

- `empresa_slug`, `nombre` y `mensaje` son obligatorios.
- Debe enviarse `telefono` o `correo`.
- La respuesta publica es:

```json
{
  "ok": true,
  "mensaje": "Mensaje recibido correctamente."
}
```

Endpoint administrativo:

```text
GET /api/contacto/mensajes/?empresa_slug=Analiza
```

## 19. APIs que faltan antes de cerrar el frontend completo

Estas APIs no bloquean empezar el frontend visual, pero si deben resolverse antes de terminar compra real.

### 19.1 Pagos

PayPal esta aprobado como primera pasarela futura, pero no esta implementado.

Falta:

- crear orden de pago;
- confirmar pago;
- webhooks;
- guardar referencia de transaccion;
- cambiar pedido a `pagado` despues de confirmacion real.

### 19.2 Descuentos aplicados al checkout

Las ofertas promocionales ya existen para la pagina Promociones.

Pendiente: aplicar esas ofertas automaticamente al carrito/pedido.

### 19.3 PDF de prefactura

La prefactura existe como JSON.

Falta generar PDF o plantilla visual imprimible.

### 19.4 Imagenes en produccion

El backend usa `media/` local para imagenes.

Para produccion falta definir almacenamiento en linea vinculado al proyecto.

### 19.5 Direcciones guardadas del cliente

El pedido ya permite direccion simple para envio local y nacional.

Falta solo si se quiere guardar una libreta de direcciones reutilizables por cliente.

## 20. Recomendacion para empezar frontend

Se puede iniciar el frontend con este orden:

1. Crear layout base de tienda.
2. Cargar empresa, branding y menu desde `GET /api/empresas/actual/?host=...`.
3. Usar `empresa.slug` para consumir catalogo publico.
4. Consumir banners promocionales por empresa.
5. Renderizar menu principal desde `empresa.menu`.
6. Consumir endpoints de paginas dinamicas segun la ruta actual.
7. Crear carrito visual local en React.
8. Crear modal/pagina de login y registro.
9. Crear flujo de verificar correo.
10. Crear flujo de recuperar contrasena.
11. Sincronizar carrito autenticado con `mi-carrito`.
12. Agregar productos por codigo de barra.
13. Implementar favoritos.
14. Capturar direccion simple para envio local/nacional.
15. Implementar formulario de contacto.
16. Mostrar pedidos y prefactura JSON.
17. Dejar pagos como pendiente hasta PayPal.

## 21. Reglas importantes para la otra conversacion

- No convertir la pagina en landing page.
- El catalogo y ventas son lo primero.
- Login debe ser secundario.
- El carrito debe estar oculto por defecto y abrirse al hacer clic.
- No agregar citas medicas.
- No duplicar acceso a "Mi cuenta".
- No dejar nombres fijos en el menu principal; usar el menu que devuelve el backend.
- No usar banners como listado de promociones; la pagina Promociones usa `promociones/ofertas/`.
- No mostrar id interno del producto al cliente.
- Para inventario interno, usar `codigo_barra` para ajustar existencias.
- Usar `empresa_slug = Analiza` como respaldo local, pero preferir resolver empresa con `/api/empresas/actual/`.
- Mantener diseno sobrio y formal.
- No integrar PayPal ni Brevo real sin autorizacion.
- No conectar Supabase sin autorizacion.

## 22. Estado final del backend para frontend

Listo para empezar frontend:

- Catalogo publico por empresa.
- Empresa publica por slug y empresa actual por host/subdominio.
- Menu principal configurable por empresa.
- Paginas dinamicas de inicio, examenes, perfiles, servicios y sucursales.
- Formulario publico de contacto.
- Banner promocional por empresa.
- Ofertas promocionales separadas de banners.
- Filtros de catalogo.
- Login JWT.
- Registro comprador.
- Verificacion de correo.
- Recuperacion de contrasena.
- Carrito y pedidos autenticados.
- Mi carrito.
- Agregar producto al carrito por codigo de barra.
- Favoritos.
- Inventario interno con productos, resumen, bajo stock, agotados y ajuste de existencia.
- Direccion simple para envio local/nacional.
- Prefactura JSON para pedidos pagados.

Pendiente para compra completa:

- PayPal;
- descuentos de productos;
- PDF de prefactura;
- almacenamiento de imagenes en produccion;
- libreta de direcciones guardadas, solo si se decide hacerla.
