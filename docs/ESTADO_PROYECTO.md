# Estado del proyecto - Sistema web de ventas en linea

Fecha de actualizacion: 2026-07-22

Este documento resume el estado actual del backend y las decisiones aprobadas. Debe actualizarse cada vez que el proyecto avance. Si una regla cambia, se debe reemplazar la regla anterior por la nueva para evitar contradicciones.

## 1. Resumen general

El proyecto es un sistema web de ventas en linea multiempresa. La primera etapa se esta construyendo en backend con Django y API REST. El frontend sera React mas adelante.

La base de datos actual es SQLite local para desarrollo. La base definitiva sera Supabase usando PostgreSQL. Cuando se conecte Supabase, las tablas, usuarios, contrasenas cifradas, pedidos, catalogo e inventario quedaran guardados en Supabase porque Django usara esa base como principal.

## 2. Tecnologias preparadas

- Backend: Django 5.2.16.
- API: Django REST Framework.
- Autenticacion API: JWT con djangorestframework-simplejwt.
- Correo transaccional: Brevo API HTTPS configurada por variables de entorno.
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
favoritos/
promociones/
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
- La empresa puede resolverse por dominio, subdominio o slug de respaldo.
- La tienda publica debera cargar la empresa segun el host actual cuando existan dominios/subdominios.

Pruebas locales sin comprar dominio:

- `analiza.localhost`
- `analiza.test`
- `GET /api/empresas/actual/?host=analiza.localhost:3000`

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

Subdominio local definido:

```text
analiza
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
- Para `envio_local` y `envio_nacional`, el pedido requiere direccion simple.
- Para `retiro_en_local`, la direccion no es obligatoria.

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

Modelo de menu por empresa:

```text
ItemMenuEmpresa
```

Campos relevantes:

- `nombre`
- `slug`
- `subdominio`
- `dominio_personalizado`
- `logo`
- `imagen_sucursales`
- `imagen_sucursales_url`
- `imagen_sucursales_final` en API publica
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
- `modo_inventario`: `inventariado`, `sin_inventario` o `mixto`
- `activa`
- `creada_por`
- fechas de creacion y actualizacion

Campos de `ItemMenuEmpresa`:

- empresa
- clave
- texto
- ruta
- orden
- activo
- abre_en_nueva_pestana
- fechas de creacion y actualizacion

Modelo de sucursales:

```text
SucursalEmpresa
```

Campos de `SucursalEmpresa`:

- empresa
- nombre
- direccion
- telefono
- horario
- google_maps_url
- imagen_final en API publica
- latitud
- longitud
- orden
- activa
- fechas de creacion y actualizacion

Reglas:

- El `slug` se genera automaticamente si no se escribe.
- `subdominio` sirve para abrir empresas como `analiza.localhost` o `analiza.tuapp.com`.
- `dominio_personalizado` sirve para dominios reales futuros como `tienda.analizahn.com`.
- `dominio_personalizado` se guarda sin `http`, sin `https` y sin puerto.
- Para resolver una empresa por host, el backend prueba primero `dominio_personalizado` exacto y despues `subdominio`.
- Si no hay dominio disponible, se mantiene el `slug` como respaldo.
- `opciones_entrega_disponibles` devuelve:
  - `envio_local`, `envio_nacional` si la empresa tiene envios.
  - `retiro_en_local` si no tiene envios.
- Cada empresa tiene su propio menu principal.
- Al crear una empresa se genera un menu predeterminado.
- El menu predeterminado contiene Inicio, Examenes, Perfiles, Servicios, Promociones, Sucursales y Contacto.
- Los nombres visibles del menu salen de `ItemMenuEmpresa.texto`.
- El frontend debe navegar usando `ItemMenuEmpresa.ruta`.
- Si un item del menu esta inactivo, no se devuelve en el menu publico.
- El orden del menu sale de `ItemMenuEmpresa.orden`.

Endpoint de resolucion por host:

```text
GET /api/empresas/actual/?host=analiza.localhost:3000
```

Tambien acepta header:

```http
X-Frontend-Host: analiza.localhost:3000
```

Respaldo por slug:

```text
GET /api/empresas/actual/?slug=Analiza
```

Endpoint solo para menu:

```text
GET /api/empresas/menu/?empresa_slug=Analiza
GET /api/empresas/menu/?host=analiza.localhost:3000
```

Endpoint publico de sucursales:

```text
GET /api/empresas/sucursales/?empresa_slug=Analiza&buscar=texto
```

La respuesta publica de sucursales devuelve `imagen_final`.
El frontend debe usar `imagen_final` para mostrar la imagen.
La imagen principal de sucursales se cambia una sola vez desde la empresa.
Si la empresa tiene `imagen_sucursales_url` o `imagen_sucursales`, todas las sucursales devuelven esa imagen en `imagen_final`.
`imagen_sucursales_url` queda preparada para almacenamiento externo futuro.

Migraciones:

- `empresas.0001_initial`
- `empresas.0002_empresa_tiene_envios`
- `empresas.0003_empresa_dominio_personalizado_empresa_subdominio`
- `empresas.0004_poblar_subdominios_existentes`
- `empresas.0005_itemmenuempresa`
- `empresas.0006_poblar_menu_empresas_existentes`
- `empresas.0007_sucursalempresa`
- `empresas.0008_alter_sucursalempresa_latitud_and_more`
- `empresas.0009_sucursalempresa_imagen_sucursalempresa_imagen_url`
- `empresas.0010_empresa_imagen_sucursales_and_more`

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
PaqueteCatalogo
PaqueteProducto
```

Reglas aprobadas:

- Una empresa tiene varias familias.
- Una familia tiene varias categorias.
- Una categoria tiene varios productos.
- Un producto pertenece a una empresa, una familia y una categoria.
- Un registro de catalogo puede ser `producto_fisico` o `servicio`.
- El codigo interno se genera automaticamente y es unico por empresa.
- El codigo de barra es unico por empresa y obligatorio solo para fisicos.
- El mismo codigo de barra puede existir en empresas diferentes.
- El `id` interno existe solo para base de datos y no debe mostrarse al cliente.
- Productos, familias y paquetes pueden usar imagen local o `imagen_url`.
- Las respuestas publicas deben usar `imagen_final`.
- `imagen_url` queda preparada para almacenamiento externo futuro.

Familia:

- empresa
- nombre
- descripcion
- imagen
- imagen_url
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
- tipo_item
- codigo_interno
- codigo_barra
- nombre
- descripcion
- imagen_principal
- imagen_url
- precio
- existencia
- existencia_minima
- orden_destacado
- activo
- fechas

PaqueteCatalogo:

- empresa
- tipo: `combo` o `perfil`
- codigo
- nombre
- descripcion
- precio_normal
- precio_paquete
- porcentaje_descuento
- imagen
- imagen_url
- destacado
- activo
- orden
- productos
- fechas

Reglas de paquetes:

- Un combo no es una promocion temporal; es un paquete vendible con precio propio.
- Un perfil es un paquete de varios productos/examenes.
- Combo y perfil usan la misma estructura interna para evitar duplicar logica.
- `precio_paquete` se devuelve como `precio_combo` en combos.
- `precio_paquete` se devuelve como `precio_perfil` en perfiles.
- Los paquetes activos se filtran por empresa.
- Combos destacados usan `destacado=True`.

Endpoints publicos dinamicos de catalogo:

```text
GET /api/catalogo/combos-destacados/?empresa_slug=Analiza
GET /api/catalogo/productos-mas-vendidos/?empresa_slug=Analiza
GET /api/catalogo/examenes/?empresa_slug=Analiza&buscar=texto
GET /api/catalogo/perfiles/?empresa_slug=Analiza&buscar=texto
GET /api/catalogo/servicios/?empresa_slug=Analiza&buscar=texto
GET /api/catalogo/servicios/detalle/?empresa_slug=Analiza&servicio=imagenes
```

Servicios:

- Se implementan usando `Familia`.
- Familia representa la rama grande de servicio.
- Categoria representa la opcion interna o grupo dentro de esa rama.
- Producto representa lo vendible.
- `/catalogo/servicios/` devuelve las ramas y un resumen de categorias.
- `/catalogo/servicios/detalle/` devuelve una rama con sus categorias y productos agrupados.

Reglas de existencia:

- Los productos fisicos inician con existencia `0`.
- Los servicios no controlan existencia y nunca aparecen agotados.
- La existencia fisica se cambia desde inventario mediante movimientos.
- `existencia_minima` sirve para alertar inventario bajo.
- Estado interno de inventario:
  - `agotado` cuando existencia es `0`;
  - `bajo` cuando existencia es mayor que `0` y menor o igual a `existencia_minima`;
  - `ok` cuando hay existencia suficiente;
  - `no_aplica` para servicios.
- Analiza esta configurada como `sin_inventario`.
- Empresas mixtas deben seleccionar el tipo al crear cada registro.
- Las ventas se cuentan desde detalles de pedidos pagados, incluso sin inventario.

Orden:

- El orden es automatico.
- En admin se muestra como solo lectura.
- Mas adelante el frontend podra reordenar con botones de subir/bajar.

Migraciones:

- `catalogo.0001_initial`
- `catalogo.0002_producto_existencia_minima`
- `catalogo.0003_familia_imagen_familia_imagen_url_and_more`
- `catalogo.0004_producto_tipo_item_y_codigo_interno`

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
- Solo los productos fisicos admiten movimientos.
- Los servicios quedan excluidos de listados, alertas y resumen de inventario.
- Una entrada suma existencia.
- Una salida resta existencia.
- Un ajuste fija la existencia final contada.
- Un ajuste puede fijar la existencia en `0`.
- Las entradas y salidas deben ser mayores que `0`.
- No se permite existencia negativa.
- Cada movimiento actualiza automaticamente `Producto.existencia`.
- Los cambios de existencia deben hacerse por movimientos para conservar historial.
- Administrador maestro, administrador de empresa y gerente pueden administrar inventario.
- Compradores no pueden administrar inventario.
- Administrador maestro puede consultar todas las empresas o filtrar por `empresa_slug`.
- Administrador de empresa y gerente solo ven los productos de su empresa.

Endpoints internos de inventario:

```text
GET /api/inventario/productos/
GET /api/inventario/resumen/
GET /api/inventario/productos-bajo-stock/
GET /api/inventario/productos-agotados/
POST /api/inventario/ajustar-existencia/
GET /api/inventario/movimientos/
POST /api/inventario/movimientos/
```

Payload para ajustar existencia por codigo de barra:

```json
{
  "codigo_barra": "ABC123",
  "existencia_nueva": 10,
  "motivo": "Conteo fisico",
  "referencia": "AJ-001"
}
```

Si un administrador maestro trabaja con codigos de barra que existen en varias empresas, debe enviar:

```json
{
  "empresa_slug": "Analiza",
  "codigo_barra": "ABC123",
  "existencia_nueva": 10
}
```

Migraciones:

- `inventario.0001_initial`
- `inventario.0002_alter_movimientoinventario_cantidad`

## 10. App favoritos

Modelo principal:

```text
Favorito
```

Campos:

- empresa
- usuario
- producto, opcional
- paquete, opcional para perfiles y combos
- fecha_creacion

Reglas:

- Un favorito pertenece a una empresa, un usuario y un solo articulo.
- El articulo puede ser un producto, servicio, examen, perfil o combo.
- Exactamente uno entre `producto` y `paquete` debe tener valor.
- Un usuario no puede duplicar el mismo articulo en la misma empresa.
- El articulo debe pertenecer a la misma empresa del favorito.
- El listado se filtra por el usuario autenticado y persiste entre sesiones.
- La API recibe `codigo` y `tipo_articulo`, sin exponer ids internos.
- La respuesta unificada usa campos `articulo_*`.

Migraciones:

- `favoritos.0001_initial`
- `favoritos.0002_favorito_paquete_alter_favorito_producto_and_more`

## 11. App promociones

Modelos principales:

```text
BannerPromocional
OfertaPromocional
OfertaProducto
```

Campos:

- empresa
- titulo
- subtitulo
- texto_boton
- url_boton
- imagen
- imagen_url
- texto_alternativo
- orden
- activo
- fecha_inicio
- fecha_fin
- fechas de creacion y actualizacion

Reglas:

- Cada banner pertenece a una empresa.
- Una empresa puede tener varios banners para carrusel o rotacion futura.
- El banner es solo carrusel visual y punto de entrada.
- El banner no representa por si mismo una oferta de la pagina Promociones.
- El campo `url_boton` puede guardar una ruta interna como `/promociones/oferta-1` o una URL externa.
- La API normal devuelve solo banners activos, vigentes y de empresas activas.
- Aunque el frontend mande token de administrador, la llamada normal no devuelve banners inactivos.
- Los administradores solo ven inactivos si envian `incluir_inactivos=true`.
- La respuesta publica no expone `id` interno ni `empresa` interna.
- `imagen_url` tiene prioridad sobre `imagen` local.
- El frontend debe usar `imagen_final`.
- `imagen` local sirve para desarrollo.
- `imagen_url` queda preparada para almacenamiento externo en produccion.
- Se puede programar inicio y fin de publicacion.
- El orden se asigna automaticamente si no se indica.

OfertaPromocional:

- empresa
- tipo: `producto`, `productos` o `paquete`
- codigo
- titulo
- descripcion
- precio_normal
- precio_oferta
- porcentaje_descuento
- imagen
- imagen_url
- url_destino
- paquete
- productos
- orden
- activo
- fecha_inicio
- fecha_fin
- fechas de creacion y actualizacion

Reglas de ofertas:

- Las ofertas se administran aparte de los banners.
- La pagina Promociones debe consumir ofertas, no banners.
- Una oferta puede ser de un producto, varios productos o un paquete/combo/perfil.
- `precio_oferta` no puede ser mayor que `precio_normal`.
- Si la oferta es tipo `paquete`, debe tener un paquete asociado.
- Los productos asociados se guardan en `OfertaProducto`.
- La API publica devuelve `imagen_final`.
- Las ofertas inactivas o fuera de vigencia no salen en la API publica.
- Administradores pueden ver inactivas usando `incluir_inactivos=true`.

Endpoint publico:

```text
GET /api/promociones/banners/?empresa_slug=Analiza
```

Endpoint publico de ofertas:

```text
GET /api/promociones/ofertas/?empresa_slug=Analiza&buscar=texto
```

Endpoint administrativo para incluir inactivos:

```text
GET /api/promociones/banners/?empresa_slug=Analiza&incluir_inactivos=true
GET /api/promociones/ofertas/?empresa_slug=Analiza&incluir_inactivos=true
```

Migraciones:

- `promociones.0001_initial`
- `promociones.0002_alter_bannerpromocional_url_boton_ofertaproducto_and_more`

## 12. App contacto

Modelo principal:

```text
MensajeContacto
```

Campos:

- empresa
- nombre
- telefono
- correo
- asunto
- mensaje
- estado
- fechas de creacion y actualizacion

Estados:

- `nuevo`
- `pendiente`
- `respondido`
- `cerrado`

Reglas:

- El endpoint publico permite crear mensajes desde el formulario de contacto.
- `empresa_slug`, `nombre` y `mensaje` son obligatorios.
- Debe enviarse telefono o correo.
- El estado inicial es `nuevo`.
- La respuesta publica no expone IDs internos.
- Administradores pueden listar mensajes por empresa.

Endpoint publico:

```text
POST /api/contacto/mensajes/
```

Endpoint administrativo:

```text
GET /api/contacto/mensajes/?empresa_slug=Analiza
```

Migraciones:

- `contacto.0001_initial`

## 13. App pedidos

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
- producto, opcional
- paquete, opcional para perfiles y combos
- cantidad
- precio_unitario
- fechas

Reglas:

- Exactamente uno entre `producto` y `paquete` debe tener valor.
- El articulo debe pertenecer a la misma empresa del carrito.
- En productos fisicos, la cantidad no puede superar la existencia disponible.
- En servicios, la cantidad no se compara contra existencia.
- Perfiles y combos validan la existencia de todos sus componentes fisicos.
- La validacion suma componentes compartidos entre diferentes lineas.
- El precio unitario se copia desde el articulo al agregarlo.
- `mi-carrito` sincroniza cambios posteriores de precio.
- Un articulo solo puede aparecer una vez dentro del mismo carrito.

### Pedido

Campos relevantes:

- empresa
- usuario
- carrito_origen
- numero automatico
- tipo_entrega
- nombre_recibe
- telefono_recibe
- direccion_entrega
- referencia_entrega
- departamento_entrega
- municipio_entrega
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
- En envio local o nacional, la direccion simple es obligatoria.
- En retiro en local, la direccion no es obligatoria.
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

Para `envio_local` o `envio_nacional`, tambien acepta:

```json
{
  "nombre_recibe": "Cliente",
  "telefono_recibe": "99999999",
  "direccion_entrega": "Direccion de entrega",
  "referencia_entrega": "Referencia",
  "departamento_entrega": "Departamento",
  "municipio_entrega": "Municipio"
}
```

Acciones:

- valida que el carrito este activo;
- valida que el carrito tenga items;
- valida que todos los articulos pertenezcan a la empresa;
- acepta productos, servicios, examenes, perfiles y combos;
- valida existencia acumulada para productos fisicos y componentes de paquetes;
- permite servicios sin existencia;
- copia items a detalles del pedido;
- guarda una fotografia de los componentes de perfiles y combos;
- calcula subtotal, impuesto, envio y total;
- aplica descuentos promocionales solamente a productos simples;
- cierra el carrito;
- evita convertir el mismo carrito dos veces.
- deja el pedido en estado `pendiente`;
- congela los importes y datos comerciales del checkout.

### DetallePedido

Campos:

- pedido
- producto o paquete
- tipo_articulo copiado
- codigo_articulo copiado
- nombre_articulo copiado
- codigo_interno copiado
- codigo_barra copiado
- nombre_producto copiado
- precio_unitario
- cantidad
- subtotal

Regla:

- El detalle conserva una copia del nombre, codigo, tipo y precio.
- Perfiles y combos guardan sus productos en `DetallePedidoComponente`.
- El pedido no cambia si luego se edita el articulo o la composicion del paquete.
- Pedido, detalle y componentes son inmutables despues del checkout.
- La API de pedidos y detalles permite solamente listar y consultar.
- No se permite crear, editar ni eliminar pedidos por las rutas genericas.
- En Django Admin solamente puede cambiarse `estado_pago` de pendiente a pagado.
- Un pedido pagado no puede regresar a pendiente.
- Cambiar una tarifa de entrega no recalcula pedidos anteriores.

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

- crea movimientos de inventario tipo `salida` solo para productos fisicos;
- descuenta existencia solo de productos fisicos;
- descuenta los componentes fisicos fotografiados de perfiles y combos;
- agrupa cantidades del mismo producto antes de crear la salida;
- registra servicios vendidos sin crear movimientos de inventario;
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
- La direccion de entrega se muestra cuando el pedido es envio local o nacional.
- El metodo de pago queda como campo informativo pendiente hasta implementar pagos.

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
- `pedidos.0007_pedido_departamento_entrega_pedido_direccion_entrega_and_more`

## 14. App pagos

Modelos:

- `Pago`: intento asociado a un pedido, con monto y moneda copiados desde la
  fotografia comercial.
- `EventoWebhookPago`: auditoria sin datos de tarjeta para controlar eventos
  repetidos del proveedor.

Estados de pago externo:

- `pendiente`
- `aprobado`
- `rechazado`

Reglas:

- Solo se inicia un pago para pedidos pendientes y con detalles.
- Solo existe un intento pendiente por pedido.
- Repetir el inicio devuelve el mismo intento pendiente.
- Un pago rechazado permite crear un intento nuevo.
- Monto, moneda, empresa y cliente se toman del pedido, no del frontend.
- El webhook requiere firma HMAC SHA-256 configurada en el entorno.
- `evento_id` es unico por proveedor y evita procesar dos veces una
  notificacion.
- Una aprobacion marca el pedido pagado dentro de una transaccion y activa el
  descuento de inventario y la prefactura.
- Pagos y eventos webhook no se eliminan; forman parte de la auditoria.
- La API de pagos es de solo lectura, excepto la accion controlada `iniciar`.
- No se guardan numeros de tarjeta, CVV ni credenciales bancarias.
- El proveedor `simulado` es solamente una base tecnica; no cobra dinero real.

Configuracion:

- `PAGOS_PROVEEDOR_DEFAULT`
- `PAGOS_WEBHOOK_SECRET`

Migracion:

- `pagos.0001_initial`

## 15. Endpoints API actuales

Rutas principales incluidas bajo `/api/`:

- `empresas/`
- `empresas/actual/`
- `empresas/menu/`
- `empresas/publica/`
- `empresas/sucursales/`
- `usuarios/registro-comprador/`
- `usuarios/login/`
- `usuarios/token/refresh/`
- `usuarios/token/verify/`
- `usuarios/perfiles/`
- `usuarios/perfiles/mi-perfil/`
- `catalogo/familias/`
- `catalogo/categorias/`
- `catalogo/productos/`
- `catalogo/combos-destacados/`
- `catalogo/productos-mas-vendidos/`
- `catalogo/examenes/`
- `catalogo/perfiles/`
- `catalogo/servicios/`
- `catalogo/servicios/detalle/`
- `contacto/mensajes/`
- `inventario/movimientos/`
- `inventario/productos/`
- `inventario/resumen/`
- `inventario/productos-bajo-stock/`
- `inventario/productos-agotados/`
- `inventario/ajustar-existencia/`
- `favoritos/`
- `promociones/banners/`
- `promociones/ofertas/`
- `pedidos/carritos/`
- `pedidos/carritos/mi-carrito/`
- `pedidos/carritos/{id}/agregar-articulo/`
- `pedidos/items-carrito/`
- `pedidos/pedidos/` (solo lectura)
- `pedidos/pedidos/{id}/prefactura/`
- `pedidos/detalles/` (solo lectura)
- `pedidos/tarifas-entrega/`
- `pagos/`
- `pagos/{referencia}/`
- `pagos/iniciar/`
- `pagos/webhooks/{proveedor}/` (solo proveedor con firma valida)

Catalogo publico:

- Las rutas de catalogo permiten lectura sin login cuando se envia `empresa_slug`.
- Ejemplo: `GET /api/catalogo/productos/?empresa_slug=Analiza`.
- La lectura publica solo devuelve empresas activas y elementos activos.
- Para crear, editar o eliminar catalogo sigue siendo obligatorio iniciar sesion y tener permisos.
- Productos aceptan filtros `buscar`, `familia`, `categoria`, `agotado` y `orden`.

## 16. Base de datos

Actual:

- SQLite local: `db.sqlite3`

Pendiente:

- Crear/conectar Supabase PostgreSQL.
- Configurar `DATABASE_URL` real.
- Ejecutar migraciones en Supabase.
- Crear superusuario en Supabase.

Nota:

El superusuario y los datos creados en SQLite local no existen automaticamente en Supabase. Cuando se cambie a Supabase se deberan crear/aplicar alli.

## 17. Autenticacion

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
- `POST /api/usuarios/token/logout/`
- `POST /api/usuarios/token/verify/`

Seguridad de sesion implementada:

- El access token dura 15 minutos.
- La sesion completa vence como maximo 5 horas despues del login.
- El limite de 5 horas no se extiende al renovar el access token.
- El refresh token se entrega unicamente como cookie `HttpOnly`.
- El frontend no debe guardar tokens en `localStorage` ni `sessionStorage`.
- El refresh y logout requieren `credentials: "include"`.
- Cerrar sesion bloquea el refresh token y elimina la cookie.

Pendiente de configuracion externa:

- Crear la clave de API de Brevo y configurarla en cada entorno autorizado.

Correo:

- El proveedor elegido para correo es Brevo.
- El envio usa la API HTTPS de Brevo para funcionar en Render sin puertos SMTP.
- `BREVO_API_KEY` y el remitente verificado se configuran por entorno.
- El backend exige confirmacion de Brevo y registra el `messageId` aceptado.
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

## 18. Pruebas realizadas

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
- Empresa publica por slug.
- Empresa actual por dominio/subdominio/host.
- Subdominio local `analiza` poblado para la empresa Analiza.
- Menu publico por empresa dentro de `empresas/actual/`.
- Endpoint publico `empresas/menu/`.
- Menu predeterminado creado para empresas existentes.
- Confirmacion de que items inactivos no salen en el menu publico.
- Sucursales publicas por empresa con busqueda.
- Examenes publicos por empresa con busqueda e `imagen_final`.
- Servicios publicos usando familias activas.
- Combos destacados publicos.
- Perfiles publicos.
- Productos mas vendidos publicos.
- Mensajes de contacto publicos.
- Listado administrativo de mensajes de contacto por empresa.
- Filtros de catalogo publico.
- Creacion/consulta de `mi-carrito`.
- Agregar producto al carrito por codigo de barra sin exponer `id` interno de producto.
- Favoritos por codigo de barra.
- Validacion de direccion obligatoria para envios local/nacional.
- Banner promocional publico por empresa.
- Filtro de banners activos y vigentes.
- Prioridad de `imagen_url` sobre imagen local mediante `imagen_final`.
- Confirmacion de que banners inactivos no salen en la tienda aunque se consulte con token admin.
- Confirmacion de que administradores pueden listar inactivos usando `incluir_inactivos=true`.
- Ofertas promocionales separadas de banners.
- Confirmacion de que la pagina Promociones consume `promociones/ofertas/`.
- Confirmacion de que banners pueden redirigir a rutas internas con `url_boton`.
- Producto creado con existencia inicial `0`.
- Listado interno de productos para inventario.
- Resumen interno de inventario.
- Filtro interno de productos agotados.
- Filtro interno de productos con inventario bajo.
- Ajuste de existencia por codigo de barra.
- Ajuste de existencia a `0`.

## 19. Pendientes recomendados en orden

1. Conectar Supabase como base PostgreSQL real.
2. Probar login JWT y registro desde el frontend o con cliente API.
3. Definir integracion PayPal cuando se autorice proveedor, credenciales y modo sandbox.
4. Crear frontend React.
5. Definir promociones/descuentos de productos.
6. Definir PDF de prefactura.
7. Definir almacenamiento de imagenes en produccion.

## 20. Reglas de trabajo pendientes de respetar

- No instalar dependencias sin autorizacion.
- No crear o modificar archivos sin autorizacion.
- No aplicar migraciones sin autorizacion.
- No conectar Supabase sin autorizacion.
- No configurar PayPal sin autorizacion.
- No crear credenciales ni escribir secretos reales en codigo.
- Cada cambio importante debe explicarse antes de ejecutarse.

## 21. Ultimo estado

El backend tiene empresas, empresa publica por slug, usuarios/perfiles, catalogo publico con filtros, inventario con resumen/listado/alertas/ajustes, favoritos, banners promocionales, carrito por codigo de barra, pedidos, prefactura PDF, login JWT, registro de compradores, verificacion de correo, recuperacion de contrasena, reportes y pago en sucursal. Usa Supabase y almacenamiento R2 por configuracion, y el correo transaccional sale por la API HTTPS de Brevo. Antes de usuarios reales deben configurarse y validarse en Render las credenciales definitivas de cada proveedor.
