# Brief para iniciar el frontend - Sistema web de ventas en linea

Fecha de preparacion: 2026-07-21

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

## 9. Empresa publica implementada

Endpoint:

```text
GET /api/empresas/publica/?slug=Analiza
```

Uso:

- cargar nombre de empresa;
- logo;
- colores;
- telefono;
- correo;
- direccion;
- sitio web;
- `tiene_envios`;
- `opciones_entrega_disponibles`.

## 10. Carrito y pedidos implementados

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

## 11. Favoritos implementados

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

## 12. Entrega

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

## 13. Totales de pedido

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

## 14. Prefactura

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

## 15. APIs que faltan antes de cerrar el frontend completo

Estas APIs no bloquean empezar el frontend visual, pero si deben resolverse antes de terminar compra real.

### 15.1 Pagos

PayPal esta aprobado como primera pasarela futura, pero no esta implementado.

Falta:

- crear orden de pago;
- confirmar pago;
- webhooks;
- guardar referencia de transaccion;
- cambiar pedido a `pagado` despues de confirmacion real.

### 15.2 Promociones y descuentos

No hay modelos ni APIs de promociones todavia.

El pedido tiene `descuento_total`, pero no existe todavia logica de promociones.

### 15.3 PDF de prefactura

La prefactura existe como JSON.

Falta generar PDF o plantilla visual imprimible.

### 15.4 Imagenes en produccion

El backend usa `media/` local para imagenes.

Para produccion falta definir almacenamiento en linea vinculado al proyecto.

### 15.5 Direcciones guardadas del cliente

El pedido ya permite direccion simple para envio local y nacional.

Falta solo si se quiere guardar una libreta de direcciones reutilizables por cliente.

## 16. Recomendacion para empezar frontend

Se puede iniciar el frontend con este orden:

1. Crear layout base de tienda.
2. Cargar branding desde `GET /api/empresas/publica/?slug=Analiza`.
3. Consumir catalogo publico con `empresa_slug=Analiza`.
4. Crear carrito visual local en React.
5. Crear modal/pagina de login y registro.
6. Crear flujo de verificar correo.
7. Crear flujo de recuperar contrasena.
8. Sincronizar carrito autenticado con `mi-carrito`.
9. Agregar productos por codigo de barra.
10. Implementar favoritos.
11. Capturar direccion simple para envio local/nacional.
12. Mostrar pedidos y prefactura JSON.
13. Dejar pagos como pendiente hasta PayPal.

## 17. Reglas importantes para la otra conversacion

- No convertir la pagina en landing page.
- El catalogo y ventas son lo primero.
- Login debe ser secundario.
- El carrito debe estar oculto por defecto y abrirse al hacer clic.
- No agregar citas medicas.
- No duplicar acceso a "Mi cuenta".
- No mostrar id interno del producto al cliente.
- Usar `empresa_slug = Analiza`.
- Mantener diseno sobrio y formal.
- No integrar PayPal ni Brevo real sin autorizacion.
- No conectar Supabase sin autorizacion.

## 18. Estado final del backend para frontend

Listo para empezar frontend:

- Catalogo publico por empresa.
- Empresa publica por slug.
- Filtros de catalogo.
- Login JWT.
- Registro comprador.
- Verificacion de correo.
- Recuperacion de contrasena.
- Carrito y pedidos autenticados.
- Mi carrito.
- Agregar producto al carrito por codigo de barra.
- Favoritos.
- Direccion simple para envio local/nacional.
- Prefactura JSON para pedidos pagados.

Pendiente para compra completa:

- PayPal;
- promociones;
- PDF de prefactura;
- almacenamiento de imagenes en produccion;
- libreta de direcciones guardadas, solo si se decide hacerla.
