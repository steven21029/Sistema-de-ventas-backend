# Registro de cambios continuos

Este documento registra las modificaciones realizadas desde el 29 de julio
de 2026. A partir de esta fecha, cada cambio aprobado del backend debe
agregarse aqui, incluyendo su impacto para el frontend cuando corresponda.

## 2026-07-29 - Seguridad y duracion de la sesion JWT

Estado: implementado y verificado.

Cambios:

- El access token paso de 30 a 15 minutos.
- La sesion completa paso de 7 dias a un maximo absoluto de 5 horas.
- Renovar el access token no extiende el limite original de la sesion.
- El refresh token dejo de exponerse en la respuesta JSON del login.
- El refresh token se guarda en una cookie `HttpOnly`.
- El endpoint de renovacion ahora lee el refresh token desde la cookie.
- Se agrego un endpoint de cierre de sesion que bloquea el refresh token.
- Se habilito el registro interno de tokens bloqueados de SimpleJWT.
- Una sesion ausente, vencida o bloqueada responde con estado HTTP `401`.
- Se agregaron pruebas para login, renovacion, limite absoluto y logout.

API afectada:

- `POST /api/usuarios/login/`
- `POST /api/usuarios/token/refresh/`
- `POST /api/usuarios/token/logout/`

Impacto para el frontend:

- Usar `credentials: "include"` en login, refresh y logout.
- Guardar el access token solamente en memoria.
- No esperar el campo `refresh` en la respuesta del login.
- Enviar un objeto vacio al endpoint de refresh.
- Al recibir `401` despues de vencer la sesion, mostrar nuevamente el login.

Archivos modificados:

- `config/settings.py`
- `usuarios/serializers.py`
- `usuarios/views.py`
- `usuarios/urls.py`
- `usuarios/tests.py`
- `.env.example`
- `docs/BRIEF_FRONTEND.md`
- `docs/ESTADO_PROYECTO.md`

Verificacion:

- Migraciones oficiales de `token_blacklist` aplicadas correctamente.
- `python manage.py check`: sin problemas.
- `python manage.py test usuarios`: 4 pruebas aprobadas.
- `python manage.py test`: 32 pruebas completas aprobadas.
- `python manage.py makemigrations --check --dry-run`: sin cambios pendientes.

### Ajuste de variables opcionales en Render

- Render puede omitir variables cuyo valor esta vacio.
- `CORS_ALLOWED_ORIGIN_REGEXES` ahora produce una lista vacia cuando no existe;
  no contiene URLs predeterminadas en `settings.py`.
- `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` y `PAGOS_WEBHOOK_SECRET` tambien son
  opcionales mientras Brevo y la pasarela real no esten activos.
- Las variables de seguridad, dominios exactos, base de datos, JWT y
  superusuario siguen siendo obligatorias.

- Aviso no bloqueante: la carpeta generada `staticfiles` aun no existe.

## 2026-07-29 - Empresas con productos fisicos y servicios

Estado: implementado, migrado y verificado por modulos.

Cambios:

- Se agregaron tres modos de empresa: `inventariado`, `sin_inventario` y `mixto`.
- Analiza quedo configurada como `sin_inventario`.
- Se agregaron los tipos `producto_fisico` y `servicio` al catalogo.
- En empresas inventariadas el tipo se asigna como producto fisico.
- En empresas sin inventario el tipo se asigna como servicio.
- En empresas mixtas la API exige seleccionar el tipo al crear.
- Cada registro recibe un `codigo_interno` automatico y unico por empresa.
- El codigo de barras quedo obligatorio solo para productos fisicos.
- Los servicios pueden tener `codigo_barra = null`.
- Los servicios no aparecen agotados y usan `estado_inventario = no_aplica`.
- Los servicios se excluyen de listados, resumen, alertas y movimientos de inventario.
- El carrito acepta `codigo` general y conserva `codigo_barra` como compatibilidad.
- El carrito valida existencia solo para productos fisicos.
- Al pagar, solo los productos fisicos generan salidas de inventario.
- Los servicios vendidos permanecen en los detalles para estadisticas y reportes.
- `productos-mas-vendidos` devuelve `total_vendido` desde pedidos pagados.
- Favoritos acepta servicios mediante el campo `codigo`.
- Promociones devuelve codigo y tipo de cada producto o servicio.
- DetallePedido conserva `codigo_interno` como dato historico.
- Se conservaron la existencia y los movimientos historicos de Analiza.

API afectada:

- `GET /api/empresas/actual/`
- `GET /api/empresas/publica/`
- APIs de productos y paginas publicas de catalogo.
- `POST /api/pedidos/carritos/{id}/agregar-producto/`
- APIs de carrito, pedidos y prefactura.
- `POST /api/favoritos/`
- APIs de promociones.
- Todas las APIs internas de inventario.

Impacto para el frontend:

- Leer `modo_inventario` al cargar la empresa.
- En empresa mixta preguntar por `tipo_item` al crear cada registro.
- Usar `codigo` para carrito y favoritos.
- Mostrar existencia solo cuando `controla_inventario` sea `true`.
- Tratar `existencia = null` como servicio, no como producto agotado.
- Ocultar inventario completo cuando la empresa use `sin_inventario`.
- Usar `total_vendido` para mostrar cantidad vendida.

Migraciones:

- `empresas.0011_empresa_modo_inventario`
- `catalogo.0004_producto_tipo_item_y_codigo_interno`
- `pedidos.0008_detallepedido_codigo_interno`

Verificacion:

- Las tres migraciones se aplicaron correctamente.
- Analiza tiene 3 servicios y conserva 1 movimiento historico.
- `python manage.py test empresas catalogo inventario pedidos`: 27 pruebas aprobadas.
- `python manage.py test favoritos promociones`: 6 pruebas aprobadas.
- `python manage.py test`: 40 pruebas completas aprobadas.

## 2026-07-29 - Motor de descuentos porcentuales

Estado: implementado, migrado y verificado por modulos.

Reglas aprobadas:

- Los descuentos se administran por empresa.
- El porcentaje permitido es de 1 a 99.
- Un descuento puede aplicarse a todos los articulos, a varios articulos
  seleccionados o a un solo articulo.
- Pueden existir varias reglas activas al mismo tiempo.
- Cada articulo recibe unicamente el descuento vigente de mayor porcentaje.
- Los porcentajes nunca se suman.
- Si dos reglas empatan, gana `individual`, luego `seleccionados` y por ultimo
  `todos`.
- Las reglas aplican tanto a productos fisicos como a servicios.
- Los banners y las ofertas visuales permanecen separados de este motor.

Cambios:

- Se agregaron `DescuentoPromocional` y `DescuentoProducto`.
- Cada regla tiene empresa, codigo, titulo, descripcion, alcance, porcentaje,
  estado y periodo opcional de vigencia.
- El administrador de Django valida la cantidad de articulos segun el alcance.
- La API valida que todos los articulos pertenezcan a la misma empresa.
- Las reglas vencidas, futuras, inactivas o mal configuradas no se aplican.
- Se agrego un servicio que resuelve una regla ganadora por articulo.
- Se agrego el calculo publico del carrito sin exigir inicio de sesion.
- El calculo publico recibe solo empresa, codigo y cantidad.
- Los precios, descuentos, impuesto y totales siempre se calculan en Django.
- Al confirmar un pedido se vuelven a consultar precios y reglas vigentes.
- Cada detalle de pedido conserva la fotografia historica del descuento.
- Los detalles antiguos conservaron su precio y subtotal como valores finales.

API de administracion y consulta:

- `GET /api/promociones/descuentos/?empresa_slug=analiza`
- `POST /api/promociones/descuentos/`
- `PATCH /api/promociones/descuentos/{id}/`
- `DELETE /api/promociones/descuentos/{id}/`
- Un administrador puede agregar `incluir_inactivos=true`.

Campos principales para crear una regla:

```json
{
  "empresa": 1,
  "codigo": "JULIO-20",
  "titulo": "Descuento de julio",
  "descripcion": "",
  "alcance": "seleccionados",
  "porcentaje": 20,
  "productos_ids": [10, 11],
  "activo": true,
  "fecha_inicio": null,
  "fecha_fin": null
}
```

Valores de `alcance`:

- `todos`: enviar `productos_ids: []`.
- `seleccionados`: enviar dos o mas identificadores.
- `individual`: enviar exactamente un identificador.

API publica para calcular el carrito:

- `POST /api/pedidos/carrito/calcular/`
- No requiere token.
- Maximo 100 articulos distintos y 999 unidades por articulo.
- Un codigo no se puede repetir dentro de la solicitud.

Ejemplo de solicitud:

```json
{
  "empresa_slug": "analiza",
  "items": [
    {
      "codigo": "ANA-000001",
      "cantidad": 2
    }
  ]
}
```

La respuesta incluye por linea:

- Datos basicos del articulo y cantidad.
- `precio_unitario`.
- `descuento_aplicado` o `null`.
- `descuento_unitario`.
- `precio_unitario_final`.
- `subtotal`.
- `descuento_total`.
- `subtotal_final`.

La respuesta general incluye:

- `subtotal`.
- `descuento_total`.
- `base_imponible`.
- `impuesto`, calculado al 15 por ciento sobre la base con descuento.
- `envio`, con valor cero porque se calcula al seleccionar la entrega.
- `total_sin_envio`.

Fotografia guardada en cada detalle de pedido:

- Codigo y titulo de la regla aplicada.
- Porcentaje aplicado.
- Precio original y precio final.
- Descuento unitario y total.
- Subtotal original y subtotal final.
- Referencia opcional a la regla, sin depender de ella para conservar el
  historial.

Migraciones:

- `promociones.0003_descuentoproducto_descuentopromocional_and_more`
- `pedidos.0009_detallepedido_descuento_promocional_and_more`

Verificacion:

- `python manage.py check`: sin problemas.
- `python manage.py makemigrations --check --dry-run`: sin cambios pendientes.

- Las dos migraciones se aplicaron correctamente.
- `python manage.py test promociones pedidos`: 13 pruebas aprobadas.
- `python manage.py test`: 46 pruebas completas aprobadas.

## 2026-07-30 - Administracion unificada de descuentos

Estado: implementado.

Cambios:

- Se oculto `Productos de descuento` del menu principal de Django Admin.
- `DescuentoProducto` se conserva como relacion interna de base de datos.
- Los productos se seleccionan dentro del formulario de cada
  `Descuento promocional`.
- Crear, configurar el alcance y activar o desactivar una regla se realiza
  desde una sola pantalla.

## 2026-07-30 - Perfiles, combos e impuesto configurable

Estado: implementado, migrado y verificado por modulos.

Reglas:

- Los descuentos promocionales se aplican solamente a productos simples.
- Los perfiles y combos no reciben descuentos promocionales.
- Cada perfil o combo conserva su precio independiente definido en
  `precio_paquete`.
- Cada empresa puede decidir si cobra o no el 15 por ciento de ISV.
- Los pedidos conservan la configuracion fiscal usada al momento de crearse.

Cambios:

- El calculador publico acepta codigos de `Producto` y `PaqueteCatalogo`.
- Los paquetes activos pueden ser de tipo `perfil` o `combo`.
- Un perfil o combo devuelve `descuento_aplicado: null`.
- Para paquetes se usa `precio_paquete` como `precio_unitario`.
- Si un paquete contiene productos fisicos, se valida su existencia.
- Se agrego `cobra_impuesto` al perfil administrativo y a las APIs de empresa.
- El calculador devuelve `cobra_impuesto` y `porcentaje_impuesto`.
- Cuando `cobra_impuesto` es falso, `impuesto` vale `0.00`.
- Se agregaron `aplica_impuesto` y `tasa_impuesto` al pedido como fotografia
  historica.
- Cambiar la configuracion fiscal de la empresa no modifica pedidos anteriores.

API publica de empresa:

- `GET /api/empresas/actual/`
- El resultado ahora incluye `cobra_impuesto`.

API publica del calculador:

- `POST /api/pedidos/carrito/calcular/`
- La solicitud conserva el mismo formato de `empresa_slug`, `codigo` y
  `cantidad`.
- En cada linea se agrego `tipo_articulo`.
- `tipo_articulo` puede ser `producto`, `perfil` o `combo`.
- La respuesta general incluye `cobra_impuesto` y `porcentaje_impuesto`.

Comportamiento fiscal:

- Empresa con impuesto: `porcentaje_impuesto = 15.00`.
- Empresa sin impuesto: `porcentaje_impuesto = 0.00` e `impuesto = 0.00`.
- El total se calcula sobre la base imponible despues del descuento de
  productos simples.

Migraciones:

- `empresas.0012_empresa_cobra_impuesto`
- `pedidos.0010_pedido_aplica_impuesto_pedido_tasa_impuesto`

Verificacion:

- Las dos migraciones se aplicaron correctamente.
- `python manage.py test empresas pedidos`: 19 pruebas aprobadas.
- `python manage.py test`: 50 pruebas completas aprobadas.

## 2026-07-30 - Importacion del catalogo de examenes

Estado: implementado, importado y verificado.

Fuente:

- `Areas-Examenes(Recuperado automaticamente).xlsx`.
- Se utilizo la hoja `PRECIOS`.
- Columnas importadas: codigo, examen, area y precio 2026.

Validacion previa:

- 328 examenes.
- 12 categorias.
- Sin codigos duplicados.
- Sin nombres duplicados.
- Sin campos obligatorios vacios.
- Sin precios invalidos o negativos.
- Los precios se redondean a dos decimales con redondeo comercial.

Destino:

- Empresa: `Analiza`.
- Familia: `Examenes`.
- Los codigos del Excel se guardaron como `codigo_barra`.
- Cada examen recibio tambien su `codigo_interno` automatico.
- Los 328 registros se crearon como servicios sin control de inventario.
- Los productos que ya existian en Analiza no fueron modificados.

Categorias y cantidades:

- `Bacteriologia`: 5.
- `Biologia molecular`: 2.
- `Coagulacion`: 11.
- `Coprologia`: 15.
- `Farmacos y drogas de abuso`: 1.
- `Hematologia`: 17.
- `Microbiologia`: 27.
- `Patologia`: 2.
- `Pruebas especiales`: 7.
- `Quimica e Inmunologia`: 231.
- `Uroanalisis`: 7.
- `Uroanalisis y Coprologia`: 3.

Comando agregado:

- `python manage.py importar_examenes_excel --archivo <archivo.xlsx>`
- Usa por defecto la empresa `Analiza`, la familia `Examenes` y la hoja
  `PRECIOS`.
- `--dry-run` valida y muestra el resumen sin guardar.
- Es idempotente: los codigos existentes se omiten y no se duplican.
- `--actualizar-existentes` permite actualizar datos solo cuando se solicita
  explicitamente.
- Toda importacion real se ejecuta dentro de una unica transaccion.

Verificacion:

- Importacion real: 12 categorias y 328 examenes creados.
- Base local: 328 importados, 328 activos y 328 servicios.
- Segunda simulacion: 0 categorias nuevas, 0 examenes nuevos y 328 existentes.
- `python manage.py test catalogo`: 9 pruebas aprobadas.
- `python manage.py test`: 50 pruebas completas aprobadas.

## 2026-07-30 - Imagenes de productos configurables por empresa

Estado: implementado, migrado y verificado.

Objetivo:

- Cada empresa decide si sus productos usan imagenes individuales.
- Las empresas con catalogos grandes de servicios pueden trabajar solamente
  con imagenes de familias y categorias.
- La configuracion inicial de `Analiza` queda sin imagenes individuales de
  productos.

Configuracion de empresa:

- Se agrego `productos_con_imagen` al perfil de empresa.
- Valor predeterminado para empresas nuevas: activo.
- El administrador maestro puede modificarlo desde Django Admin.
- La API `GET /api/empresas/actual/` devuelve `productos_con_imagen`.

Comportamiento:

- Cuando `productos_con_imagen` es verdadero, cada producto puede usar
  `imagen_principal` o `imagen_url`.
- Cuando es falso, las APIs devuelven `imagen_final: null` para los productos.
- Tambien se ocultan los campos crudos de imagen en la respuesta administrativa
  de productos.
- No se aceptan nuevas imagenes individuales mediante API, Django Admin,
  importadores ni procesos internos mientras la opcion esta desactió^=¶‰ËkºwµçD•°Ñ•áÑ¼Ù¥Í¥‰±”°•°½É‘•¸ä•°•ÍÑ…‘¼…Ñ¥Ù¼‘”(€…‘„µ½‘Õ±¼¸(´1…ÌÁ…¥¹…Ì™Õ¹¥½¹…±•Ì½¹Í•ÉÙ…¸Á±…¹Ñ¥±±…Ì½¹½¥‘…ÌÁ½È•°™É½¹Ñ•¹¸()5•¹Ô½™¥¥…°è((´¥¹¥¥½€ÕÍ„€½€¸(´•á…µ•¹•Í€ÕÍ„€½•á…µ•¹•Í€¸(´Á•É™¥±•Í€ÕÍ„€½Á•É™¥±•Í€¸(´Í•ÉÙ¥¥½Í€ÕÍ„€½Í•ÉÙ¥¥½Í€¸(´ÁÉ½µ½¥½¹•Í€ÕÍ„€½ÁÉ½µ½¥½¹•Í€¸(´ÍÕÕÉÍ…±•Í€ÕÍ„€½ÍÕÕÉÍ…±•Í€¸(´½¹Ñ…Ñ½€ÕÍ„€½½¹Ñ…Ñ½€¸(´Í½‰É•}¹½Í½ÑÉ½Í€ÕÍ„€½Í½‰É”µ¹½Í½ÑÉ½Í€¸()I•ÍÑÉ¥¥½¹•Ìè((´Q½‘„•µÁÉ•Í„¹Õ•Ù„É•¥‰”…ÕÑ½µ…Ñ¥…µ•¹Ñ”±½Ì½¡¼µ½‘Õ±½Ì¸(´±…Ù•€°ÉÕÑ…€ä…‰É•}•¹}¹Õ•Ù…}Á•ÍÑ…¹…€Í½¸¥¹µÕÑ…‰±•Ì¸(´A=MQ€ä1Q€‘”€½…Á¤½•µÁÉ•Í…Ì½¥Ñ•µÌµµ•¹Ô½€å„¹¼•ÍÑ…¸‘¥ÍÁ½¹¥‰±•Ì¸(´1„A$ä©…¹¼‘µ¥¸Í½±¼Á•Éµ¥Ñ•¸…µ‰¥…ÈÑ•áÑ½€°½É‘•¹€ä…Ñ¥Ù½€¸(´9¼Í”Á•Éµ¥Ñ•¸‘½Ìµ½‘Õ±½Ì½¸•°µ¥Íµ¼½É‘•¸‘•¹ÑÉ¼‘”Õ¹„•µÁÉ•Í„¸(´1„‰…Í”‘”‘…Ñ½ÌÉ•¡…é„±…Ù•ÌÅÕ”¹¼Á•ÉÑ•¹•é…¸…°µ•¹Ô½™¥¥…°¸(´¸©…¹¼‘µ¥¸Í”É•Ñ¥É…É½¸±…Ì½Á¥½¹•Ì‘”…É•…Èä•±¥µ¥¹…È¥Ñ•µÌ¸()½¹Ù•ÉÍ¥½¸‘”‘…Ñ½Ì±½…±•Ìè((´°¥Ñ•´M½‰É•}¹½Í½ÑÉ½Í€‘”¹…±¥é„Í”½¹Ù¥ÉÑ¥¼„Í½‰É•}¹½Í½ÑÉ½Í€¸(´MÔÉÕÑ„…µ‰¥¼‘”€½Í½‰É•¹½Í½ÑÉ½Í€„€½Í½‰É”µ¹½Í½ÑÉ½Í€¸(´M”½¹Í•ÉÙ…É½¸ÍÔÑ•áÑ¼°½É‘•¸ä•ÍÑ…‘¼…Ñ¥Ù¼¸(´1½Ìµ½‘Õ±½Ì½™¥¥…±•Ì™…±Ñ…¹Ñ•ÌÍ”½µÁ±•Ñ…É½¸Á…É„±…Ì•µÁÉ•Í…Ì•á¥ÍÑ•¹Ñ•Ì¸(´1½Ì¥Ñ•µÌ±¥‰É•ÌÅÕ”¹¼½ÉÉ•ÍÁ½¹‘¥…¸„Õ¹„Á±…¹Ñ¥±±„½™¥¥…°Í”É•Ñ¥É…É½¸¸(´1½Ì½É‘•¹•Ì‘ÕÁ±¥…‘½Ì¡•É•‘…‘½ÌÍ”¹½Éµ…±¥é…É½¸½¹Í•ÉÙ…¹‘¼ÁÉ¥µ•É¼•°(€µ½‘Õ±¼µ…Ì…¹Ñ¥Õ¼äµ½Ù¥•¹‘¼•°‘ÕÁ±¥…‘¼…°ÁÉ¥µ•È¹Õµ•É¼±¥‰É”¸(´¸¹…±¥é„°M•ÉÙ¥¥½Í€½¹Í•ÉÙ¼•°½É‘•¸€Èäá…µ•¹•Í€ÅÕ•‘¼•¸•°½É‘•¸€Ğ¸()A±…¹Ñ¥±±„M½‰É”¹½Í½ÑÉ½Ìè((´M”É•¼Õ¸É•¥ÍÑÉ¼M½‰É•9½Í½ÑÉ½ÍµÁÉ•Í…€Õ¹¼„Õ¹¼½¸…‘„•µÁÉ•Í„¸(´1½Ì…µÁ½Ì™¥©½ÌÍ½¸Ñ¥ÑÕ±¼°¥¹ÑÉ½‘Õ¥½¸°¡¥ÍÑ½É¥„°µ¥Í¥½¸°Ù¥Í¥½¸°Ù…±½É•Ì°(€½µÁÉ½µ¥Í¼°¥µ…•¸”¥µ…•¸UI0¸(´Ù…±½É•Í}±¥ÍÑ…€½¹Ù¥•ÉÑ”±…Ì±¥¹•…Ì¹¼Ù…¥…Ì‘”Ù…±½É•Í€•¸Õ¹„±¥ÍÑ„Á…É„(€•°™É½¹Ñ•¹¸(´¥µ…•¹}™¥¹…±€½¹Í•ÉÙ„½µÁ…Ñ¥‰¥±¥‘…½¸…É¡¥Ù½Ì±½…±•Ìä™ÕÑÕÉ…ÌUI1Ì‘”(€HÈ¸(´1…Ì™¥¡…ÌÍ”É•…¸…ÕÑ½µ…Ñ¥…µ•¹Ñ”Á…É„•µÁÉ•Í…Ì¹Õ•Ù…Ìäµ•‘¥…¹Ñ”µ¥É…¥½¸(€Á…É„•µÁÉ•Í…Ì•á¥ÍÑ•¹Ñ•Ì¸()A%Ìè((´AÕ‰±¥„èP€½…Á¤½•µÁÉ•Í…Ì½Í½‰É”µ¹½Í½ÑÉ½Ì¼ı•µÁÉ•Í…}Í±Õœõ¹…±¥é…€¸(´‘µ¥¹¥ÍÑÉ…Ñ¥Ù„èP½AQ €½…Á¤½•µÁÉ•Í…Ì½µ¤µÍ½‰É”µ¹½Í½ÑÉ½Ì½€¸(´1„A$ÁÕ‰±¥„¹¼•áÁ½¹”%Ì¥¹Ñ•É¹½Ì¹¤•µÁÉ•Í„¸(´M¤Í½‰É•}¹½Í½ÑÉ½Í€•ÍÑ„‘•Í…Ñ¥Ù…‘¼•¸•°µ•¹Ô°±„½¹ÍÕ±Ñ„ÁÕ‰±¥„É•ÍÁ½¹‘”(€€ĞÀÑ€¸(´‘µ¥¹¥ÍÑÉ…‘½Èµ…•ÍÑÉ¼°…‘µ¥¹¥ÍÑÉ…‘½È‘”•µÁÉ•Í„ä•É•¹Ñ”É•ÍÁ•Ñ…¸•°µ¥Íµ¼(€…¥Í±…µ¥•¹Ñ¼µÕ±Ñ¥•µÁÉ•Í„‘•°É•ÍÑ¼‘•°Á…¹•°¸(´½µÁÉ…‘½É•Ì¹¼ÁÕ•‘•¸µ½‘¥™¥…È•ÍÑ”½¹Ñ•¹¥‘¼¸()É½¹Ñ•¹è((´1„ÉÕÑ„½™¥¥…°ÅÕ”‘•‰”¥µÁ±•µ•¹Ñ…ÈI•…Ğ•Ì€½Í½‰É”µ¹½Í½ÑÉ½Í€¸(´•‰”•á¥ÍÑ¥ÈÕ¸Í½±¼½µÁ½¹•¹Ñ”™¥©¼Á…É„Ñ½‘…Ì±…Ì•µÁÉ•Í…Ì¸(´1…ÌÍ•¥½¹•ÌÙ…¥…ÌÁÕ•‘•¸½Õ±Ñ…ÉÍ”¸(´M•ÉÙ¥¥½Ì¹¼‘•‰”ÕÍ…ÉÍ”½µ¼É•ÍÁ…±‘¼Á…É„•ÍÑ„ÉÕÑ„¹¤Á…É„ÉÕÑ…Ì(€‘•Í½¹½¥‘…Ì¸(´M”…ÑÕ…±¥é…É½¸‘½Ì½A%}A91}5%9%MQIQ%Y<¹µ‘€ä(€‘½Ì½	I%}I=9Q9¹µ‘€½¸•°½¹ÑÉ…Ñ¼¹Õ•Ù¼¸()5¥É…¥½¸è((´•µÁÉ•Í…Ì¸ÀÀÄÑ}Í½‰É•¹½Í½ÑÉ½Í•µÁÉ•Í…}…±Ñ•É}¥Ñ•µµ•¹Õ•µÁÉ•Í…}±…Ù•}…¹‘}µ½É•€¸(´•µÁÉ•Í…Ì¸ÀÀÄÕ}¹½Éµ…±¥é…É}½É‘•¹}µ•¹Õ}½™¥¥…±€¸(´µ‰…ÌÅÕ•‘…É½¸…Á±¥…‘…Ì½ÉÉ•Ñ…µ•¹Ñ”•¸±„‰…Í”±½…°¸()Y•É¥™¥…¥½¸è((´ÁåÑ¡½¸µ…¹…”¹Áä¡•­€èÍ¥¸ÁÉ½‰±•µ…Ì¸(´ÁåÑ¡½¸µ…¹…”¹Áäµ…­•µ¥É…Ñ¥½¹Ì€´µ¡•¬€´µ‘ÉäµÉÕ¹€èÍ¥¸…µ‰¥½ÌÁ•¹‘¥•¹Ñ•Ì¸(´ÁåÑ¡½¸µ…¹…”¹ÁäÑ•ÍĞ•µÁÉ•Í…Í€è€ÌäÁÉÕ•‰…Ì…ÁÉ½‰…‘…Ì¸(´ÁåÑ¡½¸µ…¹…”¹ÁäÑ•ÍÑ€è€ÄĞÌÁÉÕ•‰…Ì…ÁÉ½‰…‘…Ì¸(´¥Ğ‘¥™˜€´µ¡•­€èÍ¥¸•ÉÉ½É•Ì‘”™½Éµ…Ñ¼¸((ŒŒ€ÈÀÈØ´Àà´ÀÌ€´½¹Ñ•¹¥‘¼¥¹ÍÑ¥ÑÕ¥½¹…°‘”¹…±¥é„()Õ•¹Ñ”è((´AÉ•Í•¹Ñ…¥½¸¹…±¥é„µ±¥•¹Ñ•Ì½ÉÁ½É…Ñ¥Ù½Ì€ Ä¤¹Á‘™€¸()…Ñ½Ì…É…‘½Ì•¸M½‰É•9½Í½ÑÉ½ÍµÁÉ•Í…€Á…É„±„•µÁÉ•Í„½¸Í±Õœ¹…±¥é…€è((´%¹ÑÉ½‘Õ¥½¸½¸±„ÁÉ•Í•¹¥„É•¥½¹…°ä…Ñ•¹¥½¸µ•‘¥…¹Ñ”ÍÕÕÉÍ…±•Ì•¸(€!½¹‘ÕÉ…Ì¸(´5¥Í¥½¸¥¹ÍÑ¥ÑÕ¥½¹…°¸(´Y¥Í¥½¸‘”±¥‘•É…é¼É•¥½¹…°Á…É„•°…¹¼€ÈÀÌÀ¸(´Y…±½É•Ìè…±¥‘…°%¹¹½Ù…¥½¸°M•ÉÙ¥¥¼äQ•¹½±½¥„¸(´½µÁÉ½µ¥Í¼½¸ÁÉ½å•¥½¸Í½¥…°°Õ¥‘…‘¼‘•°µ•‘¥¼…µ‰¥•¹Ñ”°µ…¹•©¼‘”(€É•Í¥‘Õ½Ì‰¥½¥¹™•¥½Í½Ìä…Á…¥Ñ…¥½¸‘•°•ÅÕ¥Á¼¸(´¡¥ÍÑ½É¥…€Á•Éµ…¹•”Ù…¥„Á½ÉÅÕ”•°‘½Õµ•¹Ñ¼¹¼¥¹±Õå”Õ¹„¡¥ÍÑ½É¥„(€•µÁÉ•Í…É¥…°¥‘•¹Ñ¥™¥…‰±”¸(´9¼Í”…Í¥¹¼Õ¹„¥µ…•¸è±…Ì¥µ…•¹•Ì‘•°‘½Õµ•¹Ñ¼™½Éµ…¸Á…ÉÑ”‘”±…Ì(€‘¥…Á½Í¥Ñ¥Ù…Ìä¹¼Í”ÕÑ¥±¥é…É½¸½µ¼É•½ÉÑ•ÌÁ…É„±„Á…¥¹„İ•ˆ¸()±…¹”è((´9¼Í”µ½‘¥™¥…É½¸µ½‘•±½Ì°µ¥É…¥½¹•Ì°Í•É¥…±¥é•ÉÌ°Ù¥ÍÑ…Ì¹¤ÉÕÑ…Ì¸(´1„A$ÁÕ‰±¥„•á¥ÍÑ•¹Ñ”É•ÍÁ½¹‘¥¼€ÈÀÁ€½¸•°½¹Ñ•¹¥‘¼µ•‘¥…¹Ñ”(€P€½…Á¤½•µÁÉ•Í…Ì½Í½‰É”µ¹½Í½ÑÉ½Ì¼ı•µÁÉ•Í…}Í±Õœõ¹…±¥é…€¸((ŒŒ€ÈÀÈØ´Àà´ÀÌ€´I•‘•ÌÍ½¥…±•ÌÁ½È•µÁÉ•Í„()½¹™¥ÕÉ…¥½¸è((´M”…É•…É½¸„µÁÉ•Í…€±…ÌUI1Ì½Á¥½¹…±•Ì¥¹ÍÑ…É…µ}ÕÉ±€°(€İ¡…ÑÍ…ÁÁ}ÕÉ±€°™…•‰½½­}ÕÉ±€äÑ¥­Ñ½­}ÕÉ±€¸(´1½Ì•¹±…•Ì‘•‰•¸ÕÍ…È!QQALäÁ•ÉÑ•¹••È…°‘½µ¥¹¥¼½™¥¥…°‘”±„É•¸(´©…¹¼‘µ¥¸µÕ•ÍÑÉ„±½ÌÕ…ÑÉ¼…µÁ½Ì‘•¹ÑÉ¼‘”I•‘•ÌÍ½¥…±•Í€¸(´P½AQ €½…Á¤½•µÁÉ•Í…Ì½µ¤µ•µÁÉ•Í„½€Á•Éµ¥Ñ”½¹ÍÕ±Ñ…Èä…ÑÕ…±¥é…È±½Ì(€•¹±…•Ì‘”±„•µÁÉ•Í„…‘µ¥¹¥ÍÑÉ…‘„¸(´1½Ì•¹±…•Ì‘”¹…±¥é„Á•Éµ…¹••¸Ù…¥½Ì¡…ÍÑ„É•¥‰¥ÈÍÕÌUI1Ì½™¥¥…±•Ì¸()½¹ÑÉ…Ñ¼ÁÕ‰±¥¼Õ¹¥¼è((´P€½…Á¤½•µÁÉ•Í…Ì½…ÑÕ…°¼ı¡½ÍĞô¸¸¹€äÍÔÉ•ÍÁ…±‘¼(€P€½…Á¤½•µÁÉ•Í…Ì½ÁÕ‰±¥„¼ıÍ±Õœõ¹…±¥é…€‘•ÙÕ•±Ù•¸•°½‰©•Ñ¼(€É•‘•Í}Í½¥…±•Í€¸(´9¼Í”É•…É½¸•¹‘Á½¥¹ÑÌ…‘¥¥½¹…±•Ì¸(´½¹Ñ…Ñ¼äM½‰É”¹½Í½ÑÉ½Ì¹¼‘ÕÁ±¥…¸±…ÌÉ•‘•Ì•¸ÍÕÌÉ•ÍÁÕ•ÍÑ…Ì¸(´°™É½¹Ñ•¹‘•‰”…É…È±„½¹™¥ÕÉ…¥½¸‘”•µÁÉ•Í„Õ¹„Ù•èäÉ•ÕÑ¥±¥é…É±„(€‘•‰…©¼‘•°¹½µ‰É”•¸½¹Ñ…Ñ¼ä…°™¥¹…°‘”M½‰É”¹½Í½ÑÉ½Ì¸(´U¹„UI0Ù…¥„¥¹‘¥„ÅÕ”•°¥½¹¼½ÉÉ•ÍÁ½¹‘¥•¹Ñ”¹¼‘•‰”µ½ÍÑÉ…ÉÍ”¸()5¥É…¥½¸äÁÉÕ•‰…Ìè((´M”É•¼ä…Á±¥¼(€•µÁÉ•Í…Ì¸ÀÀÄÙ}•µÁÉ•Í…}™…•‰½½­}ÕÉ±}•µÁÉ•Í…}¥¹ÍÑ…É…µ}ÕÉ±}…¹‘}µ½É•€¸(´ÁåÑ¡½¸µ…¹…”¹ÁäÑ•ÍĞ•µÁÉ•Í…Í€è€ĞÜÁÉÕ•‰…Ì…ÁÉ½‰…‘…Ì¸(´ÁåÑ¡½¸µ…¹…”¹ÁäÑ•ÍÑ€è€ÄÔÄÁÉÕ•‰…Ì…ÁÉ½‰…‘…Ì¸((ŒŒ€ÈÀÈØ´Àà´ÀÌ€´MÕÁ•ÉÕÍÕ…É¥¼…ÕÑ½µ…Ñ¥¼Á…É„I•¹‘•È()5½Ñ¥Ù¼è((´°Á±…¸…ÑÕ…°‘”I•¹‘•È¹¼Á•Éµ¥Ñ”ÕÍ…ÈM¡•±°ä±„‰…Í”‘•ÍÁ±•…‘„¥¹¥¥„(€Ù…¥„¸()%µÁ±•µ•¹Ñ…¥½¸è((´M”É•¼•°½µ…¹‘¼ÁåÑ¡½¸µ…¹…”¹Áä…Í•ÕÉ…É}ÍÕÁ•ÉÕÍÕ…É¥½€¸(´1•”)9=}MUAIUMI}UMI95€°)9=}MUAIUMI}5%1€ä(€)9=}MUAIUMI}AMM]=I€‘•Í‘”•°•¹Ñ½É¹¼¸(´É•„¼…ÑÕ…±¥é„•°µ¥Íµ¼ÕÍÕ…É¥¼‘”™½Éµ„¥‘•µÁ½Ñ•¹Ñ”°Í¥¸‘ÕÁ±¥…É±¼¸(´Í•ÕÉ„Á•Éµ¥Í½Ì‘”ÍÕÁ•ÉÕÍÕ…É¥¼°…•Í¼„©…¹¼‘µ¥¸°Á•É™¥°‘”(€…‘µ¥¹¥ÍÑÉ…‘½Èµ…•ÍÑÉ¼°½ÉÉ•¼Ù•É¥™¥…‘¼äÕÍÕ…É¥¼…Ñ¥Ù¼¸(´Y…±¥‘„±„½¹ÑÉ…Í•¹„½¸±…ÌÉ•±…Ì‘”Í•ÕÉ¥‘…‘”©…¹¼ä¹Õ¹„±„¥µÁÉ¥µ”(€•¸±½Ì±½Ì¸(´M”É•¼ÍÑ…ÉĞ¹Í¡€Á…É„•©•ÕÑ…Èµ¥É…¥½¹•Ì°…Í•ÕÉ…È•°ÍÕÁ•ÉÕÍÕ…É¥¼”(€¥¹¥¥…ÈÕ¹¥½É¸¸(´°MÑ…ÉĞ½µµ…¹‘”I•¹‘•È‘•‰”Í•È‰…Í ÍÑ…ÉĞ¹Í¡€¸(´1…ÌÉ•‘•¹¥…±•ÌÉ•…±•Ì¹¼Í”Õ…É‘…¸•¸¥Ğ¹¤•¸±„‘½Õµ•¹Ñ…¥½¸¸()Y•É¥™¥…¥½¸è((´ÁåÑ¡½¸µ…¹…”¹ÁäÑ•ÍĞÕÍÕ…É¥½Ì¹Ñ•ÍÑÍ}½µ…¹‘½Í€è€ĞÁÉÕ•‰…Ì…ÁÉ½‰…‘…Ì¸(´ÁåÑ¡½¸µ…¹…”¹ÁäÑ•ÍÑ€è€ÄÔÔÁÉÕ•‰…Ì…ÁÉ½‰…‘…Ì¸(´M”…É•¼‘½Ì½MA1%U}I9H¹µ‘€½¸±„½¹™¥ÕÉ…¥½¸½µÁ±•Ñ„¸((ŒŒ€ÈÀÈØ´Àà´ÀĞ€´½¹™¥ÕÉ…¥½¸•¹ÑÉ…±¥é…‘„•¸•¹Ñ½É¹¼()=‰©•Ñ¥Ù¼è((´Ù¥Ñ…ÈÙ…±½É•Ì…µ‰¥•¹Ñ…±•Ì‘ÕÁ±¥…‘½Ì‘•¹ÑÉ¼‘”½¹™¥œ½Í•ÑÑ¥¹Ì¹Áå€¸(´UÍ…È±½Ìµ¥Íµ½Ì¹½µ‰É•Ì‘•Í‘”€¹•¹Ù€•¸‘•Í…ÉÉ½±±¼ä‘•Í‘”¹Ù¥É½¹µ•¹Ğ•¸(€I•¹‘•È¸()…µ‰¥½Ìè((´MIQ}-e€°)9=}	U€°¡½ÍÑÌ°=IL°‰…Í”‘”‘…Ñ½Ì°)]P°½ÉÉ•¼äÁ…½Ì(€…¡½É„Í”±••¸µ•‘¥…¹Ñ”ÁåÑ¡½¸µ‘•½ÕÁ±•€Í¥¸Ù…±½É•Ì½¹É•Ñ½Ì‘”É•ÍÁ…±‘¼•¸(€Í•ÑÑ¥¹Ì¹Áå€¸(´M”…É•¼=IM}11=]}I9Q%1M€„±„½¹™¥ÕÉ…¥½¸•áÑ•É¹„¸(´Q	M}UI1€…¡½É„Í”±•”½¸ÁåÑ¡½¸µ‘•½ÕÁ±•€äÍ”ÁÉ½•Í„½¸(€‘¨µ‘…Ñ…‰…Í”µÕÉ±€°Á½È±¼ÅÕ”™Õ¹¥½¹„Ñ…¹Ñ¼‘•Í‘”€¹•¹Ù€½µ¼‘•Í‘”I•¹‘•È¸(´°€¹•¹Ù€±½…°Í”½µÁ±•Ñ¼½¸Ñ½‘½Ì±½Ì¹½µ‰É•ÌÉ•ÅÕ•É¥‘½Ì¸1„‰…Í”Í”(€½¹™¥ÕÉ¼¥¹¥¥…±µ•¹Ñ”½¸ME1¥Ñ”ä‘•ÍÁÕ•ÌÍ”…µ‰¥¼„MÕÁ…‰…Í”A½ÍÑÉ•ME0ì(€•°½ÉÉ•¼Á½È½¹Í½±„ä±½ÌÁ…½ÌÍ¥µÕ±…‘½ÌÍ”½¹Í•ÉÙ…¸Á…É„‘•Í…ÉÉ½±±¼¸(´€¹•¹Ø¹•á…µÁ±•€½¹Ñ¥•¹”•°µ¥Íµ¼½¹ÑÉ…Ñ¼Í¥¸É•‘•¹¥…±•ÌÉ•…±•Ì¸(´…Í•ÕÉ…É}ÍÕÁ•ÉÕÍÕ…É¥½€ÕÍ„ÁåÑ¡½¸µ‘•½ÕÁ±•€°Á•Éµ¥Ñ¥•¹‘¼±••ÈÕ¸€¹•¹Ù€(€±½…°¼Ù…É¥…‰±•Ì‘•°ÁÉ½•Í¼•¸I•¹‘•È¸(´MQQ%%1M}%IM€¥¹±Õå”ÍÑ…Ñ¥Œ½€Í½±…µ•¹Ñ”Õ…¹‘¼±„…ÉÁ•Ñ„•á¥ÍÑ”°Á½È(€±¼ÅÕ”I•¹‘•È‘•©„‘”É•Á½ÉÑ…ÈÍÑ…Ñ¥™¥±•Ì¹\ÀÀÑ€¸(´‘½Ì½MA1%U}I9H¹µ‘€¥¹±Õå”•°‰±½ÅÕ”½µÁ±•Ñ¼É•ÅÕ•É¥‘¼Á½ÈI•¹‘•È¸()Y•É¥™¥…¥½¸¥¹¥¥…°è((´ÁåÑ¡½¸µ…¹…”¹Áä¡•­€èÍ¥¸ÁÉ½‰±•µ…Ì¹¤…‘Ù•ÉÑ•¹¥…Ì‘”ÍÑ…Ñ¥™¥±•Ì¸(´1„½¹™¥ÕÉ…¥½¸Í”Ù…±¥‘¼¥¹¥¥…±µ•¹Ñ”½¸ME1¥Ñ”°=IL°)]P°½ÉÉ•¼‘”(€½¹Í½±„äÁ…½ÌÍ¥µÕ±…‘½Ì‘•Í‘”•°€¹•¹Ù€±½…°¸(´ÁåÑ¡½¸µ…¹…”¹ÁäÑ•ÍĞÕÍÕ…É¥½Ì¹Ñ•ÍÑÍ}½µ…¹‘½Í€è€ĞÁÉÕ•‰…Ì…ÁÉ½‰…‘…Ì¸(´ÁåÑ¡½¸µ…¹…”¹ÁäÑ•ÍÑ€è€ÄÔÔÁÉÕ•‰…Ì…ÁÉ½‰…‘…Ì¸(´ÁåÑ¡½¸µ…¹…”¹Áäµ…­•µ¥É…Ñ¥½¹Ì€´µ¡•¬€´µ‘ÉäµÉÕ¹€èÍ¥¸…µ‰¥½ÌÁ•¹‘¥•¹Ñ•Ì¸((ŒŒ€ÈÀÈØ´Àà´ÀĞ€´	…Í”±½…°½¹•Ñ…‘„„MÕÁ…‰…Í”A½ÍÑÉ•ME0()½¹•á¥½¸è((´°‘•Í…ÉÉ½±±¼±½…°…¡½É„ÕÍ„MÕÁ…‰…Í”A½ÍÑÉ•ME0µ•‘¥…¹Ñ”Q	M}UI1€¸(´M”ÕÑ¥±¥é„•°M•ÍÍ¥½¸Á½½±•ÈÁ½È%AØĞ°ÁÕ•ÉÑ¼€ÔĞÌÉ€ä½¹•á¥½¸MM0¸(´1„½¹ÑÉ…Í•¹„Í”½‘¥™¥¼Á…É„UI0Í¥¸µ½ÍÑÉ…É±„¹¤Õ…É‘…É±„•¸¥Ğ¸(´1„…‘•¹„½µÁ±•Ñ„•á¥ÍÑ”Í½±…µ•¹Ñ”•¸€¹•¹Ù€°ÅÕ”½¹Ñ¥¹Õ„¥¹½É…‘¼Á½È(€€¹¥Ñ¥¹½É•€¸(´‘ˆ¹ÍÅ±¥Ñ”Í€Í”½¹Í•ÉÙ„¥¹Ñ…Ñ„½µ¼½É¥•¸Á…É„ÑÉ…Í±…‘…ÈÁ½ÍÑ•É¥½Éµ•¹Ñ”(€±½Ì‘…Ñ½Ì±½…±•Ì‘”¹…±¥é„¸()É•…¥½¸‘•°•ÍÅÕ•µ„è((´M”•©•ÕÑ¼ÁåÑ¡½¸µ…¹…”¹Áäµ¥É…Ñ”€´µ¹½¥¹ÁÕÑ€½¹ÑÉ„MÕÁ…‰…Í”¸(´M”…Á±¥…É½¸Ñ½‘…Ì±…Ìµ¥É…¥½¹•Ì‘”©…¹¼ä‘”±…Ì…Á±¥…¥½¹•Ì‘•°(€ÁÉ½å•Ñ¼¸(´MÕÁ…‰…Í”½¹Ñ¥•¹”€ĞÄÑ…‰±…ÌÁÕ‰±¥…ÌÉ•…‘…ÌÁ½È©…¹¼¸(´Q½‘…Ù¥„¹¼Í”¥µÁ½ÉÑ…É½¸•µÁÉ•Í…Ì°…Ñ…±½¼°ÕÍÕ…É¥½Ì¹¤½ÑÉ½Ì‘…Ñ½Ì‘•Í‘”(€ME1¥Ñ”¸()Y•É¥™¥…¥½¸è((´1„…ÕÑ•¹Ñ¥…¥½¸äÕ¹„½¹ÍÕ±Ñ„‘”Í½±¼±•ÑÕÉ„„A½ÍÑÉ•ME0É•ÍÁ½¹‘¥•É½¸(€½ÉÉ•Ñ…µ•¹Ñ”¸(´ÁåÑ¡½¸µ…¹…”¹Áäµ¥É…Ñ”€´µ¡•­€èÍ¥¸µ¥É…¥½¹•ÌÁ•¹‘¥•¹Ñ•Ì¸(´ÁåÑ¡½¸µ…¹…”¹Áä¡•­€èÍ¥¸ÁÉ½‰±•µ…Ì‘•Ñ•Ñ…‘½Ì¸((ŒŒ€ÈÀÈØ´Àà´ÀĞ€´½µÁ…Ñ¥‰¥±¥‘…‘”ÉÕÑ…ÌA$Ù•ÉÍ¥½¹…‘…Ì()5½Ñ¥Ù¼è((´°™É½¹Ñ•¹‘•ÍÁ±•…‘¼½¹ÍÕ±Ñ„ÉÕÑ…Ì‰…©¼€½…Á¤½ØÄ½€°µ¥•¹ÑÉ…Ì•°‰…­•¹(€•áÁ½¹¥„Í½±…µ•¹Ñ”•°ÁÉ•™¥©¼€½…Á¤½€¸()…µ‰¥½Ìè((´Q½‘½Ì±½Ìµ½‘Õ±½Ì‘•°‰…­•¹…•ÁÑ…¸…¡½É„…µ‰½ÌÁÉ•™¥©½Ìè€½…Á¤½€ä(€€½…Á¤½ØÄ½€¸(´1…ÌÉÕÑ…Ì•á¥ÍÑ•¹Ñ•ÌÍ”½¹Í•ÉÙ…É½¸Á…É„¹¼É½µÁ•È¥¹Ñ•É…¥½¹•ÌÁÉ•Ù¥…Ì¸(´É•Ù•ÉÍ” ¥€½¹Ñ¥¹Õ„•¹•É…¹‘¼±…ÌÉÕÑ…Ì½É¥¥¹…±•Ì‰…©¼€½…Á¤½€¸(´M”…É•…É½¸ÁÉÕ•‰…ÌÁ…É„±„•µÁÉ•Í„…ÑÕ…°ä±„É•¹½Ù…¥½¸‘•°Ñ½­•¸)]P(€µ•‘¥…¹Ñ”•°ÁÉ•™¥©¼Ù•ÉÍ¥½¹…‘¼¸()Y•É¥™¥…¥½¸è((´ÁåÑ¡½¸µ…¹…”¹ÁäÑ•ÍĞ½¹™¥€è€ÌÁÉÕ•‰…Ì…ÁÉ½‰…‘…Ì¸(´ÁåÑ¡½¸µ…¹…”¹ÁäÑ•ÍÑ€è€ÄÔàÁÉÕ•‰…Ì…ÁÉ½‰…‘…ÌÕÍ…¹‘¼ME1¥Ñ”‘”ÁÉÕ•‰…Ì°Í¥¸(€…±Ñ•É…ÈMÕÁ…‰…Í”¸((ŒŒ€ÈÀÈØ´Àà´ÀĞ€´AÉ•Á…É…¥½¸‘”±½Õ‘™±…É”HÈÁ…É„¥µ…•¹•Ì()•Á•¹‘•¹¥…Ìè((´M”…É•…É½¸‘©…¹¼µÍÑ½É…•Í€°‰½Ñ¼Í€äÍÕÌ‘•Á•¹‘•¹¥…Ì™¥©…‘…Ì¸(´HÈÍ”¥¹Ñ•É„µ•‘¥…¹Ñ”ÍÔA$½µÁ…Ñ¥‰±”½¸LÌ¸()½¹™¥ÕÉ…¥½¸è((´HÉ}MQ=I}9	1€Á•Éµ¥Ñ”…±Ñ•É¹…È•¹ÑÉ”µ•‘¥„½€±½…°äHÈ¸(´1…ÌÉ•‘•¹¥…±•Ì°‰Õ­•Ğ°•¹‘Á½¥¹Ğ°UI0ÁÕ‰±¥„äÉ•¥½¸Í”±••¸‘•Í‘”•°(€•¹Ñ½É¹¼ä¹¼Í”Õ…É‘…¸•¸¥Ğ¸(´1½Ì%µ…•¥•±‘€ÕÍ…¸HÈÕ…¹‘¼•ÍÑ„¡…‰¥±¥Ñ…‘¼°‰…©¼•°ÁÉ•™¥©¼µ•‘¥„½€¸(´1½Ì…É¡¥Ù½ÌÉ•Á•Ñ¥‘½Ì¹¼Í½‰É•ÍÉ¥‰•¸±½Ì•á¥ÍÑ•¹Ñ•Ì¸(´1…ÌUI1ÌÁÕ‰±¥…Ì¹¼±±•Ù…¸™¥Éµ„Ñ•µÁ½É…°ä]¡¥Ñ•9½¥Í”½¹Í•ÉÙ„±„•ÍÑ¥½¸(€‘”…É¡¥Ù½Ì•ÍÑ…Ñ¥½Ì¸(´M”É•¼‘½Ì½=9%UI%=9}1=U1I}HÈ¹µ‘€½¸•°ÁÉ½•‘¥µ¥•¹Ñ¼±½…°ä(€‘”I•¹‘•È¸()½µÁ…Ñ¥‰¥±¥‘…)]Pè((´1„½½­¥”‘”É•¹½Ù…¥½¸…¡½É„ÕÍ„±„ÉÕÑ„€½…Á¤½€°Á•Éµ¥Ñ¥•¹‘¼•¹Ù¥…É±„Ñ…¹Ñ¼(€„€½…Á¤½ÕÍÕ…É¥½Ì½Ñ½­•¸½€½µ¼„€½…Á¤½ØÄ½ÕÍÕ…É¥½Ì½Ñ½­•¸½€¸(´M”…É•¼Õ¹„ÁÉÕ•‰„‘”É•¹½Ù…¥½¸Á½È±„ÉÕÑ„Ù•ÉÍ¥½¹…‘„¸()5¥É…¥½¸…½É‘…‘„è((´M½±¼Í”ÑÉ…Í±…‘…É„¹…±¥é„‘•Í‘”ME1¥Ñ”„MÕÁ…‰…Í”äHÈ¸(´1„•µÁÉ•Í„ÁÉÕ•‰…€äÑ½‘½ÌÍÕÌÉ•¥ÍÑÉ½ÌÅÕ•‘…¸•á±Õ¥‘½Ì¸()Y•É¥™¥…¥½¸¥¹¥¥…°è((´Á¥À¡•­€è‘•Á•¹‘•¹¥…Ì½¹Í¥ÍÑ•¹Ñ•Ì¸(´ÁåÑ¡½¸µ…¹…”¹Áä¡•­€è½ÉÉ•Ñ¼½¸HÈ‘•Í¡…‰¥±¥Ñ…‘¼¸(´ÁåÑ¡½¸µ…¹…”¹Áä¡•­€è½ÉÉ•Ñ¼½¸HÈ¡…‰¥±¥Ñ…‘¼ä½¹™¥ÕÉ…¥½¸™¥Ñ¥¥„¸(´=¡¼ÁÉÕ•‰…Ì‘”½¹™¥ÕÉ…¥½¸‘”ÉÕÑ…Ìä…ÕÑ•¹Ñ¥…¥½¸)]P…ÁÉ½‰…‘…Ì¸(´ÁåÑ¡½¸µ…¹…”¹ÁäÑ•ÍÑ€è€ÄÔäÁÉÕ•‰…Ì…ÁÉ½‰…‘…ÌÕÍ…¹‘¼ME1¥Ñ”‘”ÁÉÕ•‰…Ì¸(´ÁåÑ¡½¸µ…¹…”¹Áäµ…­•µ¥É…Ñ¥½¹Ì€´µ¡•¬€´µ‘ÉäµÉÕ¹€èÍ¥¸…µ‰¥½Ì‘”µ½‘•±½Ì¸(´M”½µÁ±•Ñ¼Õ¹„ÁÉÕ•‰„É•…°½¸±…ÌÉ•‘•¹¥…±•Ì±½…±•Ì‘”HÈè©…¹¼ÍÕ‰¥¼(€Õ¸½‰©•Ñ¼Ñ•µÁ½É…°°½¹™¥Éµ¼ÍÔ•á¥ÍÑ•¹¥„ä•¹•É¼ÍÔUI0ÁÕ‰±¥„¸(´1„UI0ÁÕ‰±¥„É•ÍÁ½¹‘¥¼!QQ@€ÈÀÁ€ä‘•Ù½±Ù¥¼•á…Ñ…µ•¹Ñ”•°½¹Ñ•¹¥‘¼(€…±µ…•¹…‘¼¸(´°½‰©•Ñ¼Ñ•µÁ½É…°Í”•±¥µ¥¹¼…°™¥¹…±¥é…ÈäHÈ½¹™¥Éµ¼ÅÕ”å„¹¼•á¥ÍÑ¥„¸(´1…ÌÉ•‘•¹¥…±•ÌÁ•Éµ…¹••¸Í½±…µ•¹Ñ”•¸€¹•¹Ù€°™Õ•É„‘”¥Ğ¸((ŒŒ€ÈÀÈØ´Àà´ÀĞ€´5¥É…¥½¸‘”¹…±¥é„„MÕÁ…‰…Í”ä±½Õ‘™±…É”HÈ()±…¹”ÑÉ…Í±…‘…‘¼è((´€Ä•µÁÉ•Í„è¹…±¥é„1…‰½É…Ñ½É¥½Ì±¥¹¥½Ì¸(´€à•±•µ•¹Ñ½Ì‘•°µ•¹Ô¸(´€Ä½¹Ñ•¹¥‘¼‘”M½‰É”¹½Í½ÑÉ½Ì¸(´€ÈÍÕÕÉÍ…±•Ì¸(´€È™…µ¥±¥…Ìä€ÄÔ…Ñ•½É¥…Ì¸(´€ÌÌÄÁÉ½‘ÕÑ½Ì¼Í•ÉÙ¥¥½Ì¸(´€ÄÁ…ÅÕ•Ñ”¼Á•É™¥°½¸€È½µÁ½¹•¹Ñ•Ì¸(´€Ğ‰…¹¹•ÉÌÁÉ½µ½¥½¹…±•Ì¸(´€ÄÔ¥µ…•¹•ÌÉ•±…¥½¹…‘…Ì½¸±„•µÁÉ•Í„ä•°…Ñ…±½¼¸()á±ÕÍ¥½¹•Ìè((´1„•µÁÉ•Í„ÁÉÕ•‰…€¹¼Í”½Á¥¼ä•°¥µÁ½ÉÑ…‘½È±„É•¡…é„•áÁÉ•Í…µ•¹Ñ”¸(´9¼Í”ÑÉ…Í±…‘…É½¸ÕÍÕ…É¥½Ì°…ÉÉ¥Ñ½Ì°Á•‘¥‘½Ì°Á…½Ì°™…Ù½É¥Ñ½Ì°µ•¹Í…©•Ì‘”(€½¹Ñ…Ñ¼¹¤½ÑÉ½Ìµ½Ù¥µ¥•¹Ñ½ÌÉ•…‘½ÌÁ…É„ÁÉÕ•‰…Ì¸(´‘ˆ¹ÍÅ±¥Ñ”Í€Á•Éµ…¹•”¥¹Ñ…Ñ„½µ¼É•ÍÁ…±‘¼±½…°‘•°½É¥•¸¸()%µÁ±•µ•¹Ñ…¥½¸è((´M”…É•¼±„½¹•á¥½¸½Á¥½¹…°1e}Q	M}UI1€Á…É„½¹ÍÕ±Ñ…ÈME1¥Ñ”(€½µ¼½É¥•¸Í¥¸‘•©…È‘”ÕÍ…ÈMÕÁ…‰…Í”½µ¼‰…Í”ÁÉ¥¹¥Á…°¸(´M”É•¼ÁåÑ¡½¸µ…¹…”¹Áäµ¥É…É}…¹…±¥é…}ÍÕÁ…‰…Í•€°½¸µ½‘¼€´µ‘ÉäµÉÕ¹€¸(´°½µ…¹‘¼½¹Í•ÉÙ„±…ÌÉ•±…¥½¹•ÌäÉÕÑ…Ì‘”¥µ…•¸°É•ÕÑ¥±¥é„½‰©•Ñ½Ì(€¥‘•¹Ñ¥½Ì‘”HÈäÕÍ„±…Ù•Ì¹…ÑÕÉ…±•ÌÁ…É„Á½‘•ÈÉ•Á•Ñ¥ÉÍ”Í¥¸‘ÕÁ±¥…‘½Ì¸(´1…Ì•ÍÉ¥ÑÕÉ…Ì•¸MÕÁ…‰…Í”Í”É•…±¥é…¸‘•¹ÑÉ¼‘”Õ¹„ÑÉ…¹Í…¥½¸ä±…Ì(€ÍÕ‰¥‘…Ì¹Õ•Ù…ÌÍ”•±¥µ¥¹…¸Í¤±„¥µÁ½ÉÑ…¥½¸‘”‘…Ñ½Ì™…±±„¸(´1„…É„‘”±½Ì€ÌÌÄÁÉ½‘ÕÑ½ÌÕÍ„Õ¹„½Á•É…¥½¸µ…Í¥Ù„‘”A½ÍÑÉ•ME0¸(´M”½ÉÉ¥¥¼±„½¹Í•ÉÙ…¥½¸•á…Ñ„‘”½É‘•¹•Ì½¸Ù…±½È€Á€™É•¹Ñ”„±½Ì(€½É‘•¹•Ì…ÕÑ½µ…Ñ¥½Ì‘”±½Ìµ½‘•±½Ì‘”©…¹¼¸()Y•É¥™¥…¥½¸™¥¹…°è((´1½Ì…µÁ½ÌäÉ•±…¥½¹•Ì‘•°½É¥•¸ä‘•ÍÑ¥¹¼½¥¹¥‘•¸Á…É„•µÁÉ•Í„°µ•¹Ô°(€M½‰É”¹½Í½ÑÉ½Ì°ÍÕÕÉÍ…±•Ì°™…µ¥±¥…Ì°…Ñ•½É¥…Ì°ÁÉ½‘ÕÑ½Ì°Á…ÅÕ•Ñ”°(€½µÁ½¹•¹Ñ•Ìä‰…¹¹•ÉÌ¸(´MÕÁ…‰…Í”½¹Ñ¥•¹”Í½±…µ•¹Ñ”¹…±¥é„‘•¹ÑÉ¼‘”•ÍÑ”ÑÉ…Í±…‘¼ìÁÉÕ•‰…€¹¼(€•á¥ÍÑ”•¸•°‘•ÍÑ¥¹¼¸(´1…Ì€ÄÔUI1ÌÁÕ‰±¥…Ì‘”HÈÉ•ÍÁ½¹‘¥•É½¸!QQ@€ÈÀÁ€äÍÕÌ¡…Í¡•ÌM!´ÈÔØ(€½¥¹¥‘¥•É½¸½¸±½Ì…É¡¥Ù½Ì±½…±•Ì¸(´1…ÌÉÕÑ…ÌÙ•ÉÍ¥½¹…‘…Ì‘”•µÁÉ•Í„…ÑÕ…°°Í•ÉÙ¥¥½Ì°‰…¹¹•ÉÌäM½‰É”¹½Í½ÑÉ½Ì(€É•ÍÁ½¹‘¥•É½¸!QQ@€ÈÀÁ€ÕÍ…¹‘¼±½Ì‘…Ñ½Ìµ¥É…‘½Ì¸(´ÁåÑ¡½¸µ…¹…”¹Áä¡•­€èÍ¥¸ÁÉ½‰±•µ…Ì¸(´ÁåÑ¡½¸µ…¹…”¹Áäµ…­•µ¥É…Ñ¥½¹Ì€´µ¡•¬€´µ‘ÉäµÉÕ¹€èÍ¥¸…µ‰¥½ÌÁ•¹‘¥•¹Ñ•Ì¸(´ÁåÑ¡½¸µ…¹…”¹ÁäÑ•ÍÑ€è€ÄÔäÁÉÕ•‰…Ì…ÁÉ½‰…‘…Ì½¹ÑÉ„ME1¥Ñ”Ñ•µÁ½É…°°Í¥¸(€µ½‘¥™¥…ÈMÕÁ…‰…Í”¹¤HÈ¸((ŒŒ€ÈÀÈØ´Àà´ÀØ€´1¥‰•É…¥½¸‘”½¹•á¥½¹•Ì‘•°Á½½°‘”MÕÁ…‰…Í”()5½Ñ¥Ù¼è((´°M•ÍÍ¥½¸Á½½±•È…±…¹é¼ÍÔ±¥µ¥Ñ”‘”€ÄÔ±¥•¹Ñ•Ì‘ÕÉ…¹Ñ”±…ÌÁÉÕ•‰…Ì(€±½…±•Ìä‰±½ÅÕ•¼½Á•É…¥½¹•Ì‘•°…ÉÉ¥Ñ¼½¸5a=99MMM%=9€¸(´©…¹¼½¹Í•ÉÙ…‰„…‘„½¹•á¥½¸¡…ÍÑ„€ØÀÀÍ•Õ¹‘½Ìµ•‘¥…¹Ñ”(€=99}5a}€¸()…µ‰¥½Ìè((´Q	M}=99}5a}€Í”½¹™¥ÕÉ„‘•Í‘”•°•¹Ñ½É¹¼äÕÍ„€Á€Á½È‘•™•Ñ¼¸(´…‘„Í½±¥¥ÑÕ¥•ÉÉ„ÍÔ½¹•á¥½¸…°Ñ•Éµ¥¹…È°•Ù¥Ñ…¹‘¼…ÕµÕ±…È½¹•á¥½¹•Ì(€½¥½Í…Ì•¸•°Á½½°½µÁ…ÉÑ¥‘¼¸(´€¹•¹Ø¹•á…µÁ±•€ä±„Õ¥„‘”I•¹‘•È‘½Õµ•¹Ñ…¸•°Ù…±½ÈÉ•½µ•¹‘…‘¼¸()%µÁ…Ñ¼Á…É„•°™É½¹Ñ•¹è((´1…Ì½Á•É…¥½¹•Ì…ÕÑ•¹Ñ¥…‘…Ì‘•°…ÉÉ¥Ñ¼‘•©…¸‘”½µÁ•Ñ¥È½¸½¹•á¥½¹•Ì(€É•Ñ•¹¥‘…ÌÁ½ÈÍ½±¥¥ÑÕ‘•Ì…¹Ñ•É¥½É•Ì¸()Y•É¥™¥…¥½¸è((´©…¹¼…É¼=99}5a}ôÁ€‘•Í‘”±„½¹™¥ÕÉ…¥½¸±½…°¸(´ÁåÑ¡½¸µ…¹…”¹Áä¡•­€èÍ¥¸ÁÉ½‰±•µ…Ì¸(´1„½¹ÍÕ±Ñ„‘”•µÁÉ•Í„µ•‘¥…¹Ñ”•°ÁÉ½áä±½…°‘”Y¥Ñ”É•ÍÁ½¹‘¥¼!QQ@€ÈÀÁ€¸(