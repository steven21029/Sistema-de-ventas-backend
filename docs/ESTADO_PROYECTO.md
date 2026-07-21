# Estado del proyecto - Sistema web de ventas en linea

Fecha de actualizacion: 2026-07-21

Este documento resume el estado actual del backend y las decisiones aprobadas. Debe actualizarse cada vez que el proyecto avance. Si una regla cambia, se debe reemplazar la regla anterior por la nueva para evitar contradicciones.

## 1. Resumen general

El proyecto es un sistema web de ventas en linea multiempresa. La primera etapa se esta construyendo en backend con Django y API REST. El frontend sera React mas adelante.

La base de datos actual es SQLite local para desarrollo. La base definitiva sera Supabase usando PostgreSQL. Cuando se conecte Supabase, las tablas, usuarios, contrasenas cifradas, pedidos, catalogo e inventario quedaran guardados en Supabase porque Django usara esa base como principal.

## 2. Tecnologias preparadas

- Backend: Django 5.2.16.
- API: Django REST Framework.
- Autenticacion API: JWT con djangorestframework-simplejwt.
- Correo futuro: Brevo SMTP configurado por variables de entorno, sin claves reales.
- CORS: django-cors-headers.
- Base de datos local: SQLite.
- Base de datos futura: Supabase PostgreSQL por `DATABASE_URL`.
- Variables de entorno: python-decouple.
- Conexion de base por URL: dj-database-url.
- Archivos estaticos: Whitenoise.
- Imagenes: Pillow.
- Produccion futura backend: Render.
- Produccion futura frontend: Vercel.
- Pago futuro: PayPal.

El entorno virtual existe en `.venv` y usa `pip 22.3.1`.

## 3. Estructura actual

Carpeta madre del backend:

```text
backend/
```

Carpeta hija de configuracion Django:

```text
config/
```

Apps creadas:

```text
empresas/
usuarios/
catalogo/
inventario/
pedidos/
```

Carpetas auxiliares:

```text
docs/
media/
static/
templates/
```

## 4. Configuracion general

Archivos principales:

- `manage.py`
- `config/settings.py`
- `config/urls.py`
- `.env`
- `.env.example`
- `.gitignore`
- `.python-version`
- `requirements.txt`
- `build.sh`
- `README.md`

Configuracion activa:

- `LANGUAGE_CODE = es-hn`
- `TIME_ZONE = America/Tegucigalpa`
- `STATIC_URL = static/`
- `MEDIA_URL = media/`
- Django lee `SECRET_KEY`, `DJANGO_DEBUG`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS` y `DATABASE_URL` desde variables de entorno.

## 5. Decisiones aprobadas

### Multiempresa

Version 1:

- Una sola base de datos.
- Cada registro importante se relaciona con una empresa.
- Las consultas deben filtrar por empresa cuando el usuario no sea administrador maestro.

Version futura:

- Se evaluara una version multi base de datos si el proyecto crece.

### Empresa inicial

Empresa de referencia:

```text
Analiza Laboratorios Clinicos
```

Slug definido:

```text
Analiza
```

Colores base:

- Rojo oscuro: `#d1393d`
- Rojo claro: `#e94a51`
- Azul: `#2d4b77`
- Texto: `#000000`
- Fondo: `#ffffff`

### Entregas

Cada empresa tiene el campo:

```text
tiene_envios
```

Regla:

- Si `tiene_envios = True`, la empresa ofrece `envio_local` y `envio_nacional`.
- Si `tiene_envios = False`, la empresa solo ofrece `retiro_en_local`.

### Impuesto

El impuesto inicial es 15%.

Formula aprobada:

```text
base_imponible = subtotal - descuento_total
impuesto = base_imponible * 0.15
total = base_imponible + impuesto + envio
```

El envio se suma aparte y no forma parte de la base del impuesto en esta version.

### Estados de pago

Solo se aprobaron dos estados de pago:

- `pendiente`
- `pagado`

No se usaran estados operativos como en preparacion, enviado o entregado por ahora.

## 6. App empresas

Modelo principal:

```text
Empresa
```

Campos relevantes:

- `nombre`
- `slug`
- `logo`
- `color_principal`
- `color_secundario`
- `color_acento`
- `color_texto`
- `color_fondo`
- `telefono`
- `correo`
- `direccion`
- `sitio_web`
- `tiene_envios`
- `activa`
- `creada_por`
- fechas de creacion y actualizacion

Reglas:

- El `slug` se genera automaticamente si no se escribe.
- `opciones_entrega_disponibles` devuelve:
  - `envio_local`, `envio_nacional` si la empresa tiene envios.
  - `retiro_en_local` si no tiene envios.

Migraciones:

- `empresas.0001_initial`
- `empresas.0002_empresa_tiene_envios`

## 7. App usuarios

Modelo principal:

```text
PerfilUsuario
```

Roles actuales:

- `administrador_maestro`
- `administrador_empresa`
- `gerente`
- `comprador`

Campos relevantes:

- usuario Django
- empresa
- rol
- telefono
- numero_identidad
- correo_verificado
- puede_crear_usuarios
- activo
- fechas

Reglas:

- El administrador maestro puede no tener empresa asignada.
- Administrador de empresa, gerente y comprador deben pertenecer a una empresa.
- El superusuario creado localmente tiene perfil de administrador maestro.

Implementado:

- Login con JWT por correo y contrasena.
- Registro de compradores por `empresa_slug`.
- Verificacion de correo con codigo temporal.
- Recuperacion de contrasena con codigo temporal.

Pendiente:

- Conectar Brevo con claves reales cuando se autorice.

Migraciones:

- `usuarios.0001_initial`
- `usuarios.0002_alter_perfilusuario_rol`
- `usuarios.0003_codigoverificacioncorreo`
- `usuarios.0004_perfilusuario_numero_identidad_and_more`
- `usuarios.0005_alter_codigoverificacioncorreo_tipo`

## 8. App catalogo

Modelos:

```text
Familia
Categoria
Producto
```

Reglas aprobadas:

- Una empresa tiene varias familias.
- Una familia tiene varias categorias.
- Una categoria tiene varios productos.
- Un producto pertenece a una empresa, una familia y una categoria.
- El codigo de barra es unico por empresa.
- El mismo codigo de barra puede existir en empresas diferentes.
- El `id` interno existe solo para base de datos y no debe mostrarse al cliente.
- Cada producto usa una sola imagen principal por ahora.

Familia:

- empresa
- nombre
- descripcion
- activa
- orden
- fechas

Categoria:

- empresa
- familia
- nombre
- descripcion
- activa
- orden
- fechas

Producto:

- empresa
- familia
- categoria
- codigo_barra
- nombre
- descripcion
- imagen_principal
- precio
- existencia
- activo
- fechas

Orden:

- El orden es automatico.
- En admin se muestra como solo lectura.
- Mas adelante el frontend podra reordenar con botones de subir/bajar.

Migraciones:

- `catalogo.0001_initial`

## 9. App inventario

Modelo principal:

```text
MovimientoInventario
```

Tipos:

- `entrada`
- `salida`
- `ajuste`

Campos relevantes:

- empresa
- producto
- tipo
- cantidad
- existencia_anterior
- existencia_nueva
- motivo
- referencia
- usuario
- fecha_creacion

Reglas:

- El producto debe pertenecer a la misma empresa del movimiento.
- Una entrada suma existencia.
- Una salida resta existencia.
- Un ajuste fija la existencia final contada.
- No se permite existencia negativa.
- Cada movimiento actualiza automaticamente `Producto.existencia`.
- Los cambios de existencia deben hacerse por movimientos para conservar historial.

Migraciones:

- `inventario.0001_initial`

## 10. App pedidos

Modelos:

```text
Carrito
ItemCarrito
Pedido
DetallePedido
TarifaEntrega
Prefactura
```

### Carrito

Campos:

- empresa
- usuario
- activo
- fechas

Reglas:

- Solo puede existir un carrito activo por usuario y empresa.
- El carrito calcula `total_items` y `subtotal`.

### ItemCarrito

Campos:

- carrito
- producto
- cantidad
- precio_unitario
- fechas

Reglas:

- El producto debe pertenecer a la misma empresa del carrito.
- La cantidad no puede superar la existencia disponible.
- El precio unitario se copia desde el producto al agregarlo.
- Un producto solo puede aparecer una vez dentro del mismo carrito.

### Pedido

Campos relevantes:

- empresa
- usuario
- carrito_origen
- numero automatico
- tipo_entrega
- estado_pago
- subtotal
- descuento_total
- impuesto
- envio
- total
- moneda
- observaciones
- inventario_descontado
- fechas

Tipos de entrega:

- `retiro_en_local`
- `envio_local`
- `envio_nacional`

Estados de pago:

- `pendiente`
- `pagado`

Reglas:

- Si la empresa tiene envios, solo acepta envio local o nacional.
- Si la empresa no tiene envios, solo acepta retiro en local.
- El envio se toma automaticamente de la tarifa activa si aplica.
- Retiro en local usa envio `0.00`.
- El impuesto se calcula sobre `subtotal - descuento_total`.
- El total se calcula como base imponible + impuesto + envio.
- El descuento no puede ser mayor que el subtotal.
- Todo pedido creado desde carrito inicia como `pendiente`.

### Generacion de pedido desde carrito

Endpoint implementado:

```text
POST /api/pedidos/carritos/{id}/generar-pedido/
```

Entrada esperada:

```json
{
  "tipo_entrega": "retiro_en_local",
  "observaciones": ""
}
```

Acciones:

- valida que el carrito este activo;
- valida que el carrito tenga items;
- valida que todos los productos pertenezcan a la empresa;
- valida existencia disponible;
- copia items a detalles del pedido;
- calcula subtotal, impuesto, envio y total;
- cierra el carrito;
- evita convertir el mismo carrito dos veces.

### DetallePedido

Campos:

- pedido
- producto
- codigo_barra copiado
- nombre_producto copiado
- precio_unitario
- cantidad
- subtotal

Regla:

- El detalle conserva una copia del nombre, codigo y precio para que el pedido no cambie si luego se edita el producto.

### TarifaEntrega

Campos:

- empresa
- tipo_entrega
- monto
- activa
- fechas

Reglas:

- Solo existen tarifas para `envio_local` y `envio_nacional`.
- Solo una tarifa por empresa y tipo.
- Una empresa sin envios no debe tener tarifas.
- El administrador maestro puede administrar tarifas de todas las empresas.
- El administrador de empresa solo puede administrar tarifas de su empresa.
- Gerentes y compradores no administran tarifas.

### Descuento de inventario al pagar

Cuando un pedido cambia a:

```text
pagado
```

el sistema:

- crea movimientos de inventario tipo `salida`;
- descuenta existencia de cada producto;
- usa el numero del pedido como referencia;
- marca `inventario_descontado = True`;
- evita descontar dos veces si el pedido se guarda nuevamente.
- genera una prefactura asociada al pedido pagado.

### Prefactura

La prefactura se genera para pedidos pagados.

Reglas:

- Solo existe una prefactura por pedido.
- El numero usa la base `PF-` mas el numero del pedido.
- No representa factura fiscal original.
- Se puede consultar desde `GET /api/pedidos/pedidos/{id}/prefactura/`.
- Por ahora se entrega como datos JSON, no como PDF.
- Direccion de entrega y metodo de pago quedan como campos informativos pendientes hasta implementar entrega/pagos.

Leyenda:

```text
Este documento corresponde a una prefactura y no representa una factura fiscal original.
```

Migraciones:

- `pedidos.0001_initial`
- `pedidos.0002_pedido_tipo_entrega`
- `pedidos.0003_tarifaentrega`
- `pedidos.0004_pedido_estado_pago`
- `pedidos.0005_pedido_inventario_descontado`
- `pedidos.0006_prefactura`

## 11. Endpoints API actuales

Rutas principales incluidas bajo `/api/`:

- `empresas/`
- `usuarios/registro-comprador/`
- `usuarios/login/`
- `usuarios/token/refresh/`
- `usuarios/token/verify/`
- `usuarios/perfiles/`
- `usuarios/perfiles/mi-perfil/`
- `catalogo/familias/`
- `catalogo/categorias/`
- `catalogo/productos/`
- `inventario/movimientos/`
- `pedidos/carritos/`
- `pedidos/items-carrito/`
- `pedidos/pedidos/`
- `pedidos/pedidos/{id}/prefactura/`
- `pedidos/detalles/`
- `pedidos/tarifas-entrega/`

Catalogo publico:

- Las rutas de catalogo permiten lectura sin login cuando se envia `empresa_slug`.
- Ejemplo: `GET /api/catalogo/productos/?empresa_slug=Analiza`.
- La lectura publica solo devuelve empresas activas y elementos activos.
- Para crear, editar o eliminar catalogo sigue siendo obligatorio iniciar sesion y tener permisos.

## 12. Base de datos

Actual:

- SQLite local: `db.sqlite3`

Pendiente:

- Crear/conectar Supabase PostgreSQL.
- Configurar `DATABASE_URL` real.
- Ejecutar migraciones en Supabase.
- Crear superusuario en Supabase.

Nota:

El superusuario y los datos creados en SQLite local no existen automaticamente en Supabase. Cuando se cambie a Supabase se deberan crear/aplicar alli.

## 13. Autenticacion

Decision aprobada e implementada en backend:

- Usar JWT con Django.
- Los usuarios y contrasenas se guardaran en la base usada por Django.
- Cuando se conecte Supabase, esos usuarios y hashes de contrasena quedaran en Supabase PostgreSQL.
- Login por correo y contrasena.
- Registro de compradores por `empresa_slug`.
- Verificacion de correo con codigo temporal de 6 digitos.
- Cuenta de comprador inactiva hasta verificar correo.

Endpoints actuales:

- `POST /api/usuarios/login/`
- `POST /api/usuarios/registro-comprador/`
- `POST /api/usuarios/verificar-correo/`
- `POST /api/usuarios/reenviar-verificacion/`
- `POST /api/usuarios/solicitar-recuperacion-contrasena/`
- `POST /api/usuarios/confirmar-recuperacion-contrasena/`
- `POST /api/usuarios/token/refresh/`
- `POST /api/usuarios/token/verify/`

Pendiente por implementar:

- Conectar Brevo con claves reales cuando se autorice.

Correo:

- El proveedor elegido para correo es Brevo.
- La configuracion SMTP quedo preparada con variables de entorno.
- No se han agregado claves reales.
- Mientras no se configure una clave real, el backend usa salida por consola para desarrollo.
- El codigo de verificacion vence en 15 minutos.
- El codigo tiene 6 digitos.
- El maximo de intentos por codigo es 5.
- El reenvio solo se permite despues de 1 minuto.
- La recuperacion de contrasena usa las mismas reglas de codigo temporal.
- Recuperar contrasena no activa una cuenta sin verificar.
- Al registrarse, el comprador queda con `is_active = False` y perfil `activo = False`.
- Al verificar el correo, se activan el usuario y el perfil.
- El perfil guarda `numero_identidad` hondureno de 13 digitos.
- La misma identidad no puede repetirse dentro de la misma empresa.

## 14. Pruebas realizadas

Se han ejecutado validaciones frecuentes con:

```powershell
.\.venv\Scripts\python manage.py check
.\.venv\Scripts\python manage.py makemigrations --check --dry-run
```

Resultados finales conocidos:

```text
System check identified no issues (0 silenced).
No changes detected.
```

Pruebas hechas con rollback:

- Generar pedido desde carrito con retiro en local.
- Generar pedido desde carrito con envio local y tarifa activa.
- Calculo de impuesto 15% sobre subtotal descontado.
- Descuento de inventario al marcar pedido como pagado.
- Confirmacion de que el inventario no se descuenta dos veces.
- Login JWT por correo y contrasena.
- Consulta de `mi-perfil` usando token Bearer.
- Registro de comprador por `empresa_slug`.
- Lectura publica de productos por `empresa_slug`.
- Cuenta inactiva hasta verificar correo.
- Bloqueo de identidad duplicada por empresa.
- Solicitud y confirmacion de recuperacion de contrasena.
- Generacion y consulta de prefactura para pedido pagado.

## 15. Pendientes recomendados en orden

1. Conectar Supabase como base PostgreSQL real.
2. Probar login JWT y registro desde el frontend o con cliente API.
3. Definir integracion PayPal cuando se autorice proveedor, credenciales y modo sandbox.
4. Crear frontend React.

## 16. Reglas de trabajo pendientes de respetar

- No instalar dependencias sin autorizacion.
- No crear o modificar archivos sin autorizacion.
- No aplicar migraciones sin autorizacion.
- No conectar Supabase sin autorizacion.
- No configurar PayPal sin autorizacion.
- No crear credenciales ni escribir secretos reales en codigo.
- Cada cambio importante debe explicarse antes de ejecutarse.

## 17. Ultimo estado

El backend local tiene empresas, usuarios/perfiles, catalogo publico por empresa, inventario, pedidos, prefactura, login JWT, registro de compradores, verificacion de correo y recuperacion de contrasena funcionando como base inicial. Falta conexion con Supabase, claves reales de Brevo e integracion de pago antes de usuarios reales en produccion.
