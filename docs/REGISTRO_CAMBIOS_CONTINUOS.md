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
  importadores ni procesos internos mientras la opcion esta desactivada.
- Las imagenes antiguas no se borran al desactivar la configuracion; quedan
  ocultas y pueden recuperarse si la empresa vuelve a activarla.
- Los perfiles y combos conservan sus propias imagenes porque representan una
  oferta agrupada, no un producto simple.

Imagenes de clasificacion:

- `Familia` conserva `imagen`, `imagen_url` e `imagen_final`.
- Se agregaron `imagen`, `imagen_url` e `imagen_final` a `Categoria`.
- La URL externa tiene prioridad sobre el archivo local.
- Las APIs publicas de servicios incluyen `imagen_final` tanto para la familia
  como para cada categoria.

Uso esperado en frontend:

- Consultar `productos_con_imagen` desde `/api/empresas/actual/`.
- Si es verdadero, mostrar `imagen_final` de cada producto.
- Si es falso, no reservar espacio de imagen en la tarjeta del producto.
- En las pantallas de familias y categorias, usar siempre su propio
  `imagen_final` cuando exista.
- No reutilizar automaticamente la imagen de categoria en cada uno de los
  cientos de productos; la presencia visual se mantiene en los niveles de
  familia y categoria.

Migraciones:

- `catalogo.0005_categoria_imagen_categoria_imagen_url`
- `empresas.0013_empresa_productos_con_imagen`

Verificacion:

- Las dos migraciones se aplicaron correctamente.
- La base local confirma `Analiza.productos_con_imagen = False`.
- `python manage.py check`: sin problemas.
- `python manage.py makemigrations --check --dry-run`: sin cambios pendientes.
- `python manage.py test empresas catalogo`: 24 pruebas aprobadas.
- `python manage.py test`: 53 pruebas completas aprobadas.

## 2026-07-30 - Descripciones breves del catalogo de examenes

Estado: implementado, cargado y verificado.

Alcance:

- Se agrego una descripcion informativa a cada uno de los 328 examenes
  importados del archivo de Analiza.
- Cada descripcion contiene exactamente seis palabras.
- La relacion se guarda por `codigo_barra`, evitando depender de nombres que
  puedan escribirse de formas diferentes.
- Los productos manuales `barrer` y `prueba` no se modificaron porque no
  pertenecen al archivo importado.
- La API publica de examenes ya entrega el texto mediante el campo
  `descripcion` existente.

Implementacion:

- Catalogo auditable:
  `catalogo/datos/descripciones_examenes.py`.
- Comando reproducible:
  `python manage.py agregar_descripciones_examenes`.
- Simulacion sin escritura:
  `python manage.py agregar_descripciones_examenes --dry-run`.
- El comando exige exactamente 328 entradas.
- El comando falla antes de escribir si falta algun codigo o si una
  descripcion no contiene seis palabras.
- La actualizacion se ejecuta dentro de una transaccion y es idempotente.

Fuentes medicas de referencia:

- MedlinePlus en espanol, directorio de pruebas de laboratorio:
  `https://medlineplus.gov/spanish/pruebas-de-laboratorio/`.
- CDC, directorio y conceptos de pruebas para enfermedades infecciosas:
  `https://cdc.gov/infectious-diseases-labs/php/test-directory/`.
- Mayo Clinic Laboratories, catalogo interpretativo de pruebas:
  `https://www.mayocliniclabs.com/test-catalog/`.
- NIDDK, pruebas diagnosticas de la tiroides:
  `https://www.niddk.nih.gov/health-information/informacion-de-la-salud/pruebas-diagnosticas/pruebas-tiroides`.
- American Thyroid Association, pruebas de funcion tiroidea:
  `https://www.thyroid.org/las-pruebas-de-funcion-tiroidea/`.

Consideracion clinica:

- Los textos describen de forma general para que sirve cada prueba y no
  sustituyen una indicacion, interpretacion o diagnostico medico.
- Antes de publicarlos como contenido clinico definitivo conviene que el
  director tecnico del laboratorio confirme que cada descripcion coincide con
  la metodologia y el alcance exacto ofrecido por Analiza.

Verificacion:

- Primera simulacion: 328 examenes por actualizar.
- Carga real: 328 descripciones actualizadas.
- Segunda simulacion: 0 por actualizar y 328 sin cambios.
- Base local: 328 descripciones con exactamente seis palabras.
- API publica verificada con `Hemograma Completo`.
- `python manage.py check`: sin problemas.
- `python manage.py makemigrations --check --dry-run`: sin cambios pendientes.
- `python manage.py test catalogo`: 12 pruebas aprobadas.
- `python manage.py test`: 54 pruebas completas aprobadas.

## 2026-07-30 - Favoritos persistentes para todo el catalogo

Estado: implementado, migrado y verificado por modulo.

Alcance:

- Cada favorito continua perteneciendo a una empresa y un usuario autenticado.
- Ahora puede apuntar a un producto, servicio, examen, perfil o combo.
- Los favoritos permanecen en la base de datos y vuelven a mostrarse cuando el
  cliente inicia sesion desde otro momento o dispositivo.
- Los favoritos de cada cliente se mantienen separados.

Integridad de datos:

- `producto` ahora es opcional.
- Se agrego `paquete` como referencia opcional a `PaqueteCatalogo`.
- Una restriccion exige que exactamente uno de esos campos tenga valor.
- Existen restricciones independientes para impedir duplicados de productos y
  de perfiles/combos por empresa y usuario.
- Los registros de favoritos existentes se conservan durante la migracion.

API:

- Listar: `GET /api/favoritos/?empresa_slug=Analiza`.
- Agregar: `POST /api/favoritos/`.
- Eliminar: `DELETE /api/favoritos/{id}/`.
- El payload usa `codigo` y `tipo_articulo`.
- `tipo_articulo` acepta `producto`, `perfil` o `combo`.
- Si el tipo se omite y el codigo coincide con mas de un tipo, la API exige
  indicarlo para evitar guardar el articulo equivocado.

Respuesta unificada:

- `articulo_codigo`.
- `articulo_nombre`.
- `articulo_descripcion`.
- `articulo_imagen_final`.
- `articulo_precio`.
- `articulo_agotado`.
- `articulo_familia`.
- `articulo_categoria`.
- Los campos anteriores `producto_*` se mantienen temporalmente para no romper
  integraciones existentes.

Imagenes:

- Los productos y examenes respetan `productos_con_imagen`.
- Cuando la empresa desactiva imagenes individuales, Favoritos devuelve
  `articulo_imagen_final: null` para esos productos.
- Los perfiles y combos conservan su imagen independiente.

Migracion:

- `favoritos.0002_favorito_paquete_alter_favorito_producto_and_more`

Verificacion:

- La migracion se aplico correctamente en la base local.
- `python manage.py test favoritos`: 6 pruebas aprobadas.
- `python manage.py makemigrations --check --dry-run`: sin cambios pendientes.
- `python manage.py test`: 59 pruebas completas aprobadas.

## 2026-07-30 - Carrito persistente con perfiles y combos

Estado: implementado, migrado y verificado.

Alcance:

- El carrito guardado en la base de datos ahora acepta productos fisicos,
  servicios, examenes, perfiles y combos.
- Cada item apunta exactamente a un producto o a un `PaqueteCatalogo`.
- Los articulos permanecen en `mi-carrito` entre sesiones del cliente.
- Agregar nuevamente el mismo articulo aumenta su cantidad sin crear
  duplicados.

API:

- Nueva ruta recomendada:
  `POST /api/pedidos/carritos/{id}/agregar-articulo/`.
- La ruta `agregar-producto` se conserva temporalmente como alias compatible.
- El payload usa `codigo`, `tipo_articulo` y `cantidad`.
- `tipo_articulo` acepta `producto`, `perfil` o `combo`.
- El calculador publico tambien acepta `tipo_articulo` en cada linea.
- Si un codigo coincide entre tipos y no se especifica el tipo, la solicitud se
  rechaza para evitar ambiguedad.

Respuesta de items:

- `tipo_articulo`.
- `articulo_nombre`.
- `codigo`.
- `codigo_interno`.
- `codigo_barra`.
- `tipo_item`.
- `controla_inventario`.
- `agotado`.
- `imagen_final`.
- `cantidad`.
- `precio_unitario`.
- `subtotal`.
- Se mantienen nombres anteriores como `producto_nombre` e
  `imagen_principal` durante la transicion del frontend.

Seguridad:

- El endpoint directo de items valida el propietario del carrito al crear y
  tambien al intentar mover un item.
- Un comprador no puede escribir en el carrito de otro usuario, aunque ambos
  pertenezcan a la misma empresa.
- Los carritos, productos, perfiles, combos y componentes inactivos se
  rechazan antes de guardar.

Precios y descuentos:

- Productos y servicios simples usan su precio actual.
- Perfiles y combos usan `precio_paquete`.
- `mi-carrito` sincroniza el precio persistido cuando cambia el precio actual.
- Los descuentos promocionales siguen aplicandose solamente a productos
  simples.
- Perfiles y combos conservan su precio independiente y descuento cero.

Inventario:

- Los servicios no controlan existencia.
- Cada perfil o combo valida sus componentes fisicos.
- La validacion suma cantidades cuando varios paquetes comparten un producto.
- El calculador publico y el carrito persistente aplican la misma regla.
- Al pagar se agrupan las salidas del mismo producto para evitar descuentos
  parciales o duplicados.

Fotografia historica del pedido:

- `DetallePedido` ahora puede apuntar a producto o paquete.
- Se agregaron `tipo_articulo`, `codigo_articulo` y `nombre_articulo`.
- Se creo `DetallePedidoComponente` para fotografiar los productos incluidos
  en perfiles y combos.
- Si la composicion del paquete cambia despues de comprar, el pedido conserva
  los componentes originales.
- El inventario se descuenta usando esa fotografia historica.
- La respuesta de pedido y la prefactura incluyen `componentes`.
- Los detalles de pedidos existentes se completan automaticamente durante la
  migracion.

Migracion:

- `pedidos.0011_detallepedidocomponente_alter_itemcarrito_options_and_more`

Verificacion:

- La migracion se aplico correctamente en la base local.
- `python manage.py test pedidos`: 13 pruebas aprobadas.
- `python manage.py check`: sin problemas.
- `python manage.py makemigrations --check --dry-run`: sin cambios pendientes.
- `python manage.py test`: 65 pruebas completas aprobadas.

## 2026-07-30 - Limpieza del flujo de carrito y pedidos

Codigo simplificado:

- `AgregarProductoCarritoSerializer` se renombro internamente a
  `AgregarArticuloCarritoSerializer`, porque procesa productos, perfiles y
  combos.
- Las opciones validas de `tipo_articulo` se centralizaron para no mantener
  dos listas iguales.
- Se retiro la validacion individual de existencia del calculador publico,
  porque la validacion acumulada posterior cubre cada linea y tambien los
  productos compartidos entre paquetes.
- El calculador publico ahora rechaza perfiles o combos que contengan un
  componente inactivo, igual que el carrito persistente y la generacion del
  pedido.

Compatibilidad conservada intencionalmente:

- `agregar-producto` continua como alias temporal de `agregar-articulo`.
- `codigo_barra` continua como entrada alternativa temporal de `codigo`.
- `producto_nombre`, `imagen_principal` y `producto_nombre_actual` permanecen
  en las respuestas mientras el frontend termina de adoptar los nombres
  genericos.
- Estos elementos no son codigo muerto: forman parte del contrato anterior
  documentado para el frontend y retirarlos ahora podria romper una
  integracion pendiente.

Auditoria:

- No se encontraron imports, clases nuevas, rutas internas ni metodos del
  flujo actualizado sin referencias.
- Los archivos de `pedidos` compilan correctamente.
- `python manage.py test pedidos`: 14 pruebas aprobadas.
- `python manage.py test`: 66 pruebas completas aprobadas.
- `python manage.py check`: sin problemas.
- `python manage.py makemigrations --check --dry-run`: sin cambios pendientes.

## 2026-07-31 - Retiro del contrato antiguo del carrito

El frontend termino la migracion al carrito unificado. Desde esta fecha queda
un solo contrato oficial para productos, servicios, examenes, perfiles y
combos.

Elementos retirados:

- Ruta `POST /api/pedidos/carritos/{id}/agregar-producto/`.
- Entrada alternativa `codigo_barra` al agregar un articulo. Ahora el payload
  exige `codigo`.
- Campo duplicado `producto_nombre` en los items del carrito.
- Campo duplicado `imagen_principal` en los items del carrito.
- Campo duplicado `producto_nombre_actual` en los detalles del pedido.

Contrato vigente:

- Ruta `POST /api/pedidos/carritos/{id}/agregar-articulo/`.
- Entrada con `codigo`, `tipo_articulo` y `cantidad`.
- Items con `articulo_nombre` e `imagen_final`.
- Detalles de pedido con `nombre_articulo` como valor historico.

Alcance:

- `codigo_barra` permanece como dato de salida para productos que tengan
  codigo de barras; solo se retiro como nombre alternativo del payload.
- `imagen_principal` permanece en el modelo y las APIs del catalogo; solo se
  retiro su duplicado en la respuesta del carrito.
- Las notas anteriores sobre compatibilidad quedan conservadas unicamente
  como historial y ya no describen el contrato vigente.

Verificacion:

- La ruta antigua responde `404 Not Found`.
- El payload con solo `codigo_barra` responde `400 Bad Request` y exige
  `codigo`.
- Las respuestas del carrito ya no contienen `producto_nombre` ni
  `imagen_principal`.
- Los detalles del pedido ya no contienen `producto_nombre_actual`.
- `python manage.py test pedidos`: 16 pruebas aprobadas.
- `python manage.py test`: 68 pruebas completas aprobadas.
- `python manage.py check`: sin problemas.
- `python manage.py makemigrations --check --dry-run`: sin cambios pendientes.

## 2026-07-31 - Fotografia comercial inmutable del checkout

La fotografia del pedido ya no es solamente una copia inicial. Desde este
cambio tambien queda protegida contra modificaciones posteriores.

Datos congelados:

- Empresa, cliente y carrito de origen.
- Numero y tipo de entrega.
- Destinatario, telefono y direccion.
- Subtotal, descuento, impuesto, tarifa de envio y total.
- Moneda y observaciones.
- Tipo, codigo, nombre, precio y cantidad de cada articulo.
- Promocion aplicada y valores finales de cada linea.
- Componentes incluidos originalmente en perfiles y combos.

Reglas:

- Cambiar productos, paquetes, impuestos o tarifas no altera pedidos creados.
- Al marcar como pagado no se recalcula la tarifa ni el total.
- Pago, descuento de inventario y creacion de prefactura se ejecutan dentro de
  una misma transaccion.
- Un pedido pagado no puede volver a pendiente.
- Pedido, detalles y componentes no pueden eliminarse como registros
  ordinarios.
- Las APIs `pedidos/pedidos` y `pedidos/detalles` son de solo lectura.
- En Django Admin los datos comerciales son de solo lectura y unicamente se
  permite cambiar `estado_pago`.
- `articulo_nombre_actual` se retiro de la respuesta. El frontend debe usar
  `nombre_articulo`, que representa el valor historico comprado.

Verificacion:

- `python manage.py test pedidos`: 19 pruebas aprobadas.
- `python manage.py test`: 71 pruebas completas aprobadas.
- `python manage.py check`: sin problemas.
- `python manage.py makemigrations --check --dry-run`: sin cambios pendientes.

## 2026-07-31 - Base neutral de pagos y webhooks

Se creo la app independiente `pagos` para conectar una pasarela sin acoplarla
al carrito ni a los modelos comerciales del pedido.

Modelos:

- `Pago` conserva pedido, empresa, cliente, referencia UUID, proveedor, monto,
  moneda, estado, identificador externo y fechas.
- `EventoWebhookPago` registra el identificador del evento, hash del payload,
  resultado y estado de procesamiento sin guardar datos sensibles.

API:

- `POST /api/pagos/iniciar/` crea o recupera el intento pendiente.
- `GET /api/pagos/` lista los pagos visibles para el usuario o personal de la
  empresa.
- `GET /api/pagos/{referencia}/` consulta un intento por su referencia publica.
- `POST /api/pagos/webhooks/{proveedor}/` recibe resultados firmados del
  proveedor.

Seguridad e integridad:

- El frontend solo envia `pedido_id`; monto y moneda siempre salen del pedido.
- Un cliente no puede iniciar ni consultar pagos de otro cliente.
- Solo existe un pago pendiente por pedido.
- Los eventos repetidos con el mismo contenido son idempotentes.
- Reutilizar `evento_id` con otro contenido se rechaza.
- La firma se valida con HMAC SHA-256 y comparacion de tiempo constante.
- Un pago solo cambia de estado mediante un webhook verificado.
- La aprobacion, el cambio del pedido, el inventario y la prefactura se
  procesan de forma atomica.
- Pagos confirmados y eventos se conservan como auditoria.
- No se almacenan datos de tarjeta, CVV ni credenciales bancarias.

Configuracion agregada:

- `PAGOS_PROVEEDOR_DEFAULT`
- `PAGOS_WEBHOOK_SECRET`

Estado de integracion:

- La base neutral y el proveedor local `simulado` estan preparados.
- Todavia no existe un cobro real ni una URL de redireccion.
- Al elegir la pasarela se implementara su adaptador de inicio, firma y
  traduccion de estados.

Migracion:

- `pagos.0001_initial`

Verificacion:

- `python manage.py test pagos`: 7 pruebas aprobadas.
- `python manage.py test pagos pedidos`: 26 pruebas aprobadas.
- `python manage.py test`: 78 pruebas completas aprobadas.
- `python manage.py check`: sin problemas.
- `python manage.py makemigrations --check --dry-run`: sin cambios pendientes.
- `pagos.0001_initial`: aplicada correctamente en la base local.

## 2026-07-31 - Cuentas locales para pruebas de roles

Se prepararon dos cuentas en la base local. Sus correos y contrasenas no se
versionan y deben configurarse de forma segura en cada entorno.

Superadministrador:

- Usuario de Django Admin: `admin`
- Rol: `administrador_maestro`
- Empresa fija: ninguna
- Cuenta activa y verificada.

Comprador de Analiza:

- Usuario: `compras`
- Rol: `comprador`
- Empresa: `Analiza`
- Cuenta activa y verificada.

Decision multiempresa:

- La supercuenta utilizara una sola identidad para administrar cualquier empresa.
- La empresa activa se determinara mediante dominio, subdominio o slug.
- La cuenta compradora permanece vinculada exclusivamente con Analiza.
- Antes del frontend administrativo se debe centralizar el contexto de empresa
  en las APIs.

Seguridad:

- Estas credenciales son exclusivamente para desarrollo local.
- Deben cambiarse antes de publicar el sistema o permitir acceso desde internet.
- No se crearon migraciones ni se modificaron archivos de codigo.

## 2026-08-03 - APIs completas para el panel administrativo React

Estado: implementado, migrado, documentado y verificado.

Objetivo:

- Preparar el backend del panel administrativo sin modificar el frontend.
- Mantener las APIs publicas actuales de la tienda.
- Aplicar el aislamiento multiempresa en el servidor y no confiar en IDs de
  empresa recibidos desde React.
- Ejecutar el trabajo en ocho fases consecutivas, verificando cada modulo antes
  de avanzar al siguiente.

Contexto multiempresa:

- Se agrego middleware para resolver la empresa mediante dominio, subdominio,
  `X-Frontend-Host` o `empresa_slug` durante desarrollo local.
- Se agrego `GET /api/empresas/contexto-administrativo/` para devolver usuario,
  perfil, empresa actual, empresas disponibles y permisos.
- Se agrego `GET/PATCH /api/empresas/mi-empresa/` para configuracion visual y
  comercial de la empresa actual.
- `PerfilUsuario` ahora tiene `empresas_permitidas` para limitar el alcance del
  administrador maestro.
- Administrador de empresa y gerente quedan forzados a su empresa aunque el
  JSON intente enviar otra.
- Las solicitudes explicitas hacia una empresa no permitida responden `403`.

Empresa, menu y sucursales:

- Se creo CRUD administrativo de menu en `/api/empresas/items-menu/`.
- Clave y orden del menu son unicos dentro de cada empresa.
- Se amplio `/api/empresas/sucursales/` con CRUD autenticado, busqueda, orden,
  paginacion e inclusion opcional de inactivas.
- La consulta publica de sucursales conserva su lista sin paginar y solo
  devuelve sucursales activas.
- Branding, colores, logo, imagen general de sucursales, datos de contacto,
  envios, impuesto e imagenes de productos se pueden modificar desde
  `mi-empresa`.
- Slug, dominios, modo de inventario y activacion de empresa permanecen bajo
  control del superusuario.

Catalogo y paquetes:

- El permiso de catalogo ahora reconoce `administrador_empresa`.
- Familias, categorias y productos tienen CRUD administrativo paginado, filtros
  por empresa, busqueda, orden e inclusion de inactivos.
- El serializador administrativo de producto devuelve su `id` interno.
- `existencia` permanece de solo lectura y solo cambia mediante inventario.
- Se agrego CRUD `/api/catalogo/paquetes/` para perfiles y combos.
- Cada componente del paquete recibe `producto_id`, `cantidad` y `orden`.
- La cantidad del componente participa en validacion del carrito, disponibilidad
  y descuento de inventario.
- Paquetes activos no pueden quedar vacios ni mezclar productos de empresas.
- Las eliminaciones protegidas por historial responden `409`.

Promociones:

- Banners, ofertas y descuentos continúan como tres recursos independientes.
- Los CRUD de `/api/promociones/banners/`, `/api/promociones/ofertas/` y
  `/api/promociones/descuentos/` quedaron aislados por empresas permitidas.
- Se agregaron busqueda, orden, paginacion opcional e inclusion de inactivos.
- Las ofertas reciben `productos_ids` para uno o varios productos segun su tipo.
- Todas las relaciones se validan contra la empresa actual.

Usuarios y sesiones:

- Se agrego CRUD sin eliminacion en `/api/usuarios/administracion/`.
- Superusuario crea administradores maestros y cualquier rol empresarial.
- Administrador maestro gestiona roles de sus empresas permitidas.
- Administrador de empresa gestiona gerentes y compradores.
- Gerente gestiona compradores solo cuando tiene
  `puede_crear_usuarios=true`.
- Comprador no tiene acceso al panel.
- Se agregaron filtros por texto, rol, estado, empresa y orden.
- La contrasena nunca aparece en las respuestas.
- Las acciones `bloquear` y `desbloquear` cambian tanto el perfil como el usuario
  Django.
- Bloquear, desactivar o cambiar contrasena revoca todos los refresh tokens.
- Crear sin `correo_verificado=true` deja la cuenta inactiva.
- El login rechaza perfiles con correo sin verificar.

Contactos, pedidos y pagos:

- Contactos permite creacion publica y bandeja administrativa aislada por
  empresa.
- En un mensaje administrativo solo se puede modificar `estado`; nombre,
  contacto y contenido quedan como historial.
- Pedidos y detalles siguen siendo de solo lectura y ahora admiten filtros por
  estado, cliente, busqueda, fechas y orden.
- Administrador de empresa y gerente pueden consultar todos los pedidos de su
  empresa; compradores solo los propios.
- Pagos ahora devuelve empresa y cliente para la bandeja administrativa.
- Se agregaron filtros por estado, proveedor, cliente, referencia, fechas y
  orden.
- Pedidos y pagos conservan su inmutabilidad; los estados de pago solo cambian
  mediante el flujo controlado y webhook firmado.

Paginacion y errores:

- Se agrego paginacion administrativa de 20 registros y maximo 100 mediante
  `tamano_pagina`.
- Promociones, contactos, pedidos y pagos aceptan `paginar=true` para conservar
  compatibilidad con respuestas anteriores.
- Los rangos de fecha usan `fecha_desde` y `fecha_hasta` en formato
  `AAAA-MM-DD`.
- Se estandarizo `409 Conflict` cuando una eliminacion esta bloqueada por
  historial relacionado.

Migraciones:

- `usuarios.0006_perfilusuario_empresas_permitidas`.
- `catalogo.0006_paqueteproducto_cantidad`.
- Ambas quedaron aplicadas en la base local.

Documentacion para frontend:

- Se creo `docs/API_PANEL_ADMINISTRATIVO.md` como contrato oficial del panel
  React.
- Incluye autenticacion, contexto de empresa, matriz de roles, endpoints,
  filtros, paginacion, imagenes, errores y reglas de eliminacion.
- `docs/BRIEF_FRONTEND.md` ahora enlaza este contrato para reemplazar secciones
  antiguas que marcaban estas APIs como pendientes.

Verificacion final:

- `python manage.py check`: sin problemas.
- `python manage.py makemigrations --check --dry-run`: sin cambios pendientes.
- `catalogo.0006` y `usuarios.0006`: aplicadas.
- `python manage.py test`: 134 pruebas aprobadas.
- `git diff --check`: sin errores de formato.
- Aviso no bloqueante: la carpeta generada `staticfiles` aun no existe.

Fuera de alcance de este cambio:

- No se modifico el proyecto frontend.
- No se conecto Supabase.
- No se integro una pasarela real ni credenciales de produccion.

## 2026-08-03 - Menu de modulos oficiales y plantilla Sobre nosotros

Estado: implementado, migrado, documentado y verificado.

Decision funcional:

- Se descarto la creacion de paginas y rutas genericas.
- Todas las empresas usan el mismo conjunto de modulos oficiales.
- Cada empresa solo cambia el texto visible, el orden y el estado activo de
  cada modulo.
- Las paginas funcionales conservan plantillas conocidas por el frontend.

Menu oficial:

- `inicio` usa `/`.
- `examenes` usa `/examenes`.
- `perfiles` usa `/perfiles`.
- `servicios` usa `/servicios`.
- `promociones` usa `/promociones`.
- `sucursales` usa `/sucursales`.
- `contacto` usa `/contacto`.
- `sobre_nosotros` usa `/sobre-nosotros`.

Restricciones:

- Toda empresa nueva recibe automaticamente los ocho modulos.
- `clave`, `ruta` y `abre_en_nueva_pestana` son inmutables.
- `POST` y `DELETE` de `/api/empresas/items-menu/` ya no estan disponibles.
- La API y Django Admin solo permiten cambiar `texto`, `orden` y `activo`.
- No se permiten dos modulos con el mismo orden dentro de una empresa.
- La base de datos rechaza claves que no pertenezcan al menu oficial.
- En Django Admin se retiraron las opciones de agregar y eliminar items.

Conversion de datos locales:

- El item `Sobre_nosotros` de Analiza se convirtio a `sobre_nosotros`.
- Su ruta cambio de `/sobrenosotros` a `/sobre-nosotros`.
- Se conservaron su texto, orden y estado activo.
- Los modulos oficiales faltantes se completaron para las empresas existentes.
- Los items libres que no correspondian a una plantilla oficial se retiraron.
- Los ordenes duplicados heredados se normalizaron conservando primero el
  modulo mas antiguo y moviendo el duplicado al primer numero libre.
- En Analiza, `Servicios` conservo el orden 2 y `Examenes` quedo en el orden 4.

Plantilla Sobre nosotros:

- Se creo un registro `SobreNosotrosEmpresa` uno a uno con cada empresa.
- Los campos fijos son titulo, introduccion, historia, mision, vision, valores,
  compromiso, imagen e imagen URL.
- `valores_lista` convierte las lineas no vacias de `valores` en una lista para
  el frontend.
- `imagen_final` conserva compatibilidad con archivos locales y futuras URLs de
  R2.
- Las fichas se crean automaticamente para empresas nuevas y mediante migracion
  para empresas existentes.

APIs:

- Publica: `GET /api/empresas/sobre-nosotros/?empresa_slug=Analiza`.
- Administrativa: `GET/PATCH /api/empresas/mi-sobre-nosotros/`.
- La API publica no expone IDs internos ni empresa.
- Si `sobre_nosotros` esta desactivado en el menu, la consulta publica responde
  `404`.
- Administrador maestro, administrador de empresa y gerente respetan el mismo
  aislamiento multiempresa del resto del panel.
- Compradores no pueden modificar este contenido.

Frontend:

- La ruta oficial que debe implementar React es `/sobre-nosotros`.
- Debe existir un solo componente fijo para todas las empresas.
- Las secciones vacias pueden ocultarse.
- Servicios no debe usarse como respaldo para esta ruta ni para rutas
  desconocidas.
- Se actualizaron `docs/API_PANEL_ADMINISTRATIVO.md` y
  `docs/BRIEF_FRONTEND.md` con el contrato nuevo.

Migracion:

- `empresas.0014_sobrenosotrosempresa_alter_itemmenuempresa_clave_and_more`.
- `empresas.0015_normalizar_orden_menu_oficial`.
- Ambas quedaron aplicadas correctamente en la base local.

Verificacion:

- `python manage.py check`: sin problemas.
- `python manage.py makemigrations --check --dry-run`: sin cambios pendientes.
- `python manage.py test empresas`: 39 pruebas aprobadas.
- `python manage.py test`: 143 pruebas aprobadas.
- `git diff --check`: sin errores de formato.

## 2026-08-03 - Contenido institucional de Analiza

Fuente:

- `Presentacion Analiza-Clientes Corporativos (1).pdf`.

Datos cargados en `SobreNosotrosEmpresa` para la empresa con slug `Analiza`:

- Introduccion con la presencia regional y atencion mediante sucursales en
  Honduras.
- Mision institucional.
- Vision de liderazgo regional para el ano 2030.
- Valores: Calidad, Innovacion, Servicio y Tecnologia.
- Compromiso con proyeccion social, cuidado del medio ambiente, manejo de
  residuos bioinfecciosos y capacitacion del equipo.
- `historia` permanece vacia porque el documento no incluye una historia
  empresarial identificable.
- No se asigno una imagen: las imagenes del documento forman parte de las
  diapositivas y no se utilizaron como recortes para la pagina web.

Alcance:

- No se modificaron modelos, migraciones, serializers, vistas ni rutas.
- La API publica existente respondio `200` con el contenido mediante
  `GET /api/empresas/sobre-nosotros/?empresa_slug=Analiza`.

## 2026-08-03 - Redes sociales por empresa

Configuracion:

- Se agregaron a `Empresa` las URLs opcionales `instagram_url`,
  `whatsapp_url`, `facebook_url` y `tiktok_url`.
- Los enlaces deben usar HTTPS y pertenecer al dominio oficial de la red.
- Django Admin muestra los cuatro campos dentro de `Redes sociales`.
- `GET/PATCH /api/empresas/mi-empresa/` permite consultar y actualizar los
  enlaces de la empresa administrada.
- Los enlaces de Analiza permanecen vacios hasta recibir sus URLs oficiales.

Contrato publico unico:

- `GET /api/empresas/actual/?host=...` y su respaldo
  `GET /api/empresas/publica/?slug=Analiza` devuelven el objeto
  `redes_sociales`.
- No se crearon endpoints adicionales.
- Contacto y Sobre nosotros no duplican las redes en sus respuestas.
- El frontend debe cargar la configuracion de empresa una vez y reutilizarla
  debajo del nombre en Contacto y al final de Sobre nosotros.
- Una URL vacia indica que el icono correspondiente no debe mostrarse.

Migracion y pruebas:

- Se creo y aplico
  `empresas.0016_empresa_facebook_url_empresa_instagram_url_and_more`.
- `python manage.py test empresas`: 47 pruebas aprobadas.
- `python manage.py test`: 151 pruebas aprobadas.

## 2026-08-03 - Superusuario automatico para Render

Motivo:

- El plan actual de Render no permite usar Shell y la base desplegada inicia
  vacia.

Implementacion:

- Se creo el comando `python manage.py asegurar_superusuario`.
- Lee `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL` y
  `DJANGO_SUPERUSER_PASSWORD` desde el entorno.
- Crea o actualiza el mismo usuario de forma idempotente, sin duplicarlo.
- Asegura permisos de superusuario, acceso a Django Admin, perfil de
  administrador maestro, correo verificado y usuario activo.
- Valida la contrasena con las reglas de seguridad de Django y nunca la imprime
  en los logs.
- Se creo `start.sh` para ejecutar migraciones, asegurar el superusuario e
  iniciar Gunicorn.
- El Start Command de Render debe ser `bash start.sh`.
- Las credenciales reales no se guardan en Git ni en la documentacion.

Verificacion:

- `python manage.py test usuarios.tests_comandos`: 4 pruebas aprobadas.
- `python manage.py test`: 155 pruebas aprobadas.
- Se agrego `docs/DESPLIEGUE_RENDER.md` con la configuracion completa.

## 2026-08-04 - Configuracion centralizada en entorno

Objetivo:

- Evitar valores ambientales duplicados dentro de `config/settings.py`.
- Usar los mismos nombres desde `.env` en desarrollo y desde Environment en
  Render.

Cambios:

- `SECRET_KEY`, `DJANGO_DEBUG`, hosts, CORS, base de datos, JWT, correo y pagos
  ahora se leen mediante `python-decouple` sin valores concretos de respaldo en
  `settings.py`.
- Se agrego `CORS_ALLOW_CREDENTIALS` a la configuracion externa.
- `DATABASE_URL` ahora se lee con `python-decouple` y se procesa con
  `dj-database-url`, por lo que funciona tanto desde `.env` como desde Render.
- El `.env` local se completo con todos los nombres requeridos. La base se
  configuro inicialmente con SQLite y despues se cambio a Supabase PostgreSQL;
  el correo por consola y los pagos simulados se conservan para desarrollo.
- `.env.example` contiene el mismo contrato sin credenciales reales.
- `asegurar_superusuario` usa `python-decouple`, permitiendo leer un `.env`
  local o variables del proceso en Render.
- `STATICFILES_DIRS` incluye `static/` solamente cuando la carpeta existe, por
  lo que Render deja de reportar `staticfiles.W004`.
- `docs/DESPLIEGUE_RENDER.md` incluye el bloque completo requerido por Render.

Verificacion inicial:

- `python manage.py check`: sin problemas ni advertencias de staticfiles.
- La configuracion se valido inicialmente con SQLite, CORS, JWT, correo de
  consola y pagos simulados desde el `.env` local.
- `python manage.py test usuarios.tests_comandos`: 4 pruebas aprobadas.
- `python manage.py test`: 155 pruebas aprobadas.
- `python manage.py makemigrations --check --dry-run`: sin cambios pendientes.

## 2026-08-04 - Base local conectada a Supabase PostgreSQL

Conexion:

- El desarrollo local ahora usa Supabase PostgreSQL mediante `DATABASE_URL`.
- Se utiliza el Session pooler por IPv4, puerto `5432` y conexion SSL.
- La contrasena se codifico para URL sin mostrarla ni guardarla en Git.
- La cadena completa existe solamente en `.env`, que continua ignorado por
  `.gitignore`.
- `db.sqlite3` se conserva intacta como origen para trasladar posteriormente
  los datos locales de Analiza.

Creacion del esquema:

- Se ejecuto `python manage.py migrate --noinput` contra Supabase.
- Se aplicaron todas las migraciones de Django y de las aplicaciones del
  proyecto.
- Supabase contiene 41 tablas publicas creadas por Django.
- Todavia no se importaron empresas, catalogo, usuarios ni otros datos desde
  SQLite.

Verificacion:

- La autenticacion y una consulta de solo lectura a PostgreSQL respondieron
  correctamente.
- `python manage.py migrate --check`: sin migraciones pendientes.
- `python manage.py check`: sin problemas detectados.

## 2026-08-04 - Compatibilidad de rutas API versionadas

Motivo:

- El frontend desplegado consulta rutas bajo `/api/v1/`, mientras el backend
  exponia solamente el prefijo `/api/`.

Cambios:

- Todos los modulos del backend aceptan ahora ambos prefijos: `/api/` y
  `/api/v1/`.
- Las rutas existentes se conservaron para no romper integraciones previas.
- `reverse()` continua generando las rutas originales bajo `/api/`.
- Se agregaron pruebas para la empresa actual y la renovacion del token JWT
  mediante el prefijo versionado.

Verificacion:

- `python manage.py test config`: 3 pruebas aprobadas.
- `python manage.py test`: 158 pruebas aprobadas usando SQLite de pruebas, sin
  alterar Supabase.

## 2026-08-04 - Preparacion de Cloudflare R2 para imagenes

Dependencias:

- Se agregaron `django-storages`, `boto3` y sus dependencias fijadas.
- R2 se integra mediante su API compatible con S3.

Configuracion:

- `R2_STORAGE_ENABLED` permite alternar entre `media/` local y R2.
- Las credenciales, bucket, endpoint, URL publica y region se leen desde el
  entorno y no se guardan en Git.
- Los `ImageField` usan R2 cuando esta habilitado, bajo el prefijo `media/`.
- Los archivos repetidos no sobrescriben los existentes.
- Las URLs publicas no llevan firma temporal y WhiteNoise conserva la gestion
  de archivos estaticos.
- Se creo `docs/CONFIGURACION_CLOUDFLARE_R2.md` con el procedimiento local y
  de Render.

Compatibilidad JWT:

- La cookie de renovacion ahora usa la ruta `/api/`, permitiendo enviarla tanto
  a `/api/usuarios/token/` como a `/api/v1/usuarios/token/`.
- Se agrego una prueba de renovacion por la ruta versionada.

Migracion acordada:

- Solo se trasladara Analiza desde SQLite a Supabase y R2.
- La empresa `prueba` y todos sus registros quedan excluidos.

Verificacion inicial:

- `pip check`: dependencias consistentes.
- `python manage.py check`: correcto con R2 deshabilitado.
- `python manage.py check`: correcto con R2 habilitado y configuracion ficticia.
- Ocho pruebas de configuracion de rutas y autenticacion JWT aprobadas.
- `python manage.py test`: 159 pruebas aprobadas usando SQLite de pruebas.
- `python manage.py makemigrations --check --dry-run`: sin cambios de modelos.
- Se completo una prueba real con las credenciales locales de R2: Django subio
  un objeto temporal, confirmo su existencia y genero su URL publica.
- La URL publica respondio HTTP `200` y devolvio exactamente el contenido
  almacenado.
- El objeto temporal se elimino al finalizar y R2 confirmo que ya no existia.
- Las credenciales permanecen solamente en `.env`, fuera de Git.

## 2026-08-04 - Migracion de Analiza a Supabase y Cloudflare R2

Alcance trasladado:

- 1 empresa: Analiza Laboratorios Clinicos.
- 8 elementos del menu.
- 1 contenido de Sobre nosotros.
- 2 sucursales.
- 2 familias y 15 categorias.
- 331 productos o servicios.
- 1 paquete o perfil con 2 componentes.
- 4 banners promocionales.
- 15 imagenes relacionadas con la empresa y el catalogo.

Exclusiones:

- La empresa `prueba` no se copio y el importador la rechaza expresamente.
- No se trasladaron usuarios, carritos, pedidos, pagos, favoritos, mensajes de
  contacto ni otros movimientos creados para pruebas.
- `db.sqlite3` permanece intacta como respaldo local del origen.

Implementacion:

- Se agrego la conexion opcional `LEGACY_DATABASE_URL` para consultar SQLite
  como origen sin dejar de usar Supabase como base principal.
- Se creo `python manage.py migrar_analiza_supabase`, con modo `--dry-run`.
- El comando conserva las relaciones y rutas de imagen, reutiliza objetos
  identicos de R2 y usa claves naturales para poder repetirse sin duplicados.
- Las escrituras en Supabase se realizan dentro de una transaccion y las
  subidas nuevas se eliminan si la importacion de datos falla.
- La carga de los 331 productos usa una operacion masiva de PostgreSQL.
- Se corrigio la conservacion exacta de ordenes con valor `0` frente a los
  ordenes automaticos de los modelos de Django.

Verificacion final:

- Los campos y relaciones del origen y destino coinciden para empresa, menu,
  Sobre nosotros, sucursales, familias, categorias, productos, paquete,
  componentes y banners.
- Supabase contiene solamente Analiza dentro de este traslado; `prueba` no
  existe en el destino.
- Las 15 URLs publicas de R2 respondieron HTTP `200` y sus hashes SHA-256
  coincidieron con los archivos locales.
- Las rutas versionadas de empresa actual, servicios, banners y Sobre nosotros
  respondieron HTTP `200` usando los datos migrados.
- `python manage.py check`: sin problemas.
- `python manage.py makemigrations --check --dry-run`: sin cambios pendientes.
- `python manage.py test`: 159 pruebas aprobadas contra SQLite temporal, sin
  modificar Supabase ni R2.

## 2026-08-06 - Liberacion de conexiones del pool de Supabase

Motivo:

- El Session pooler alcanzo su limite de 15 clientes durante las pruebas
  locales y bloqueo operaciones del carrito con `EMAXCONNSESSION`.
- Django conservaba cada conexion hasta 600 segundos mediante
  `CONN_MAX_AGE`.

Cambios:

- `DATABASE_CONN_MAX_AGE` se configura desde el entorno y usa `0` por defecto.
- Cada solicitud cierra su conexion al terminar, evitando acumular conexiones
  ociosas en el pool compartido.
- `.env.example` y la guia de Render documentan el valor recomendado.

Impacto para el frontend:

- Las operaciones autenticadas del carrito dejan de competir con conexiones
  retenidas por solicitudes anteriores.

Verificacion:

- Django cargo `CONN_MAX_AGE=0` desde la configuracion local.
- `python manage.py check`: sin problemas.
- La consulta de empresa mediante el proxy local de Vite respondio HTTP `200`.

## 2026-08-06 - Reportes comerciales administrativos

Estado: implementado y verificado.

Cambios:

- Se agrego `GET /api/v1/reportes/resumen-ventas/` con filtros de empresa,
  fechas, agrupacion diaria o mensual y comparacion contra el periodo anterior.
- Los ingresos usan la fotografia historica de pedidos pagados o con pago
  aprobado. Pendientes, rechazados y cancelados se clasifican por separado.
- Se agregaron serie temporal, desglose por estado y productos mas vendidos.
- Se agrego `GET /api/v1/reportes/ventas/exportar/` para CSV, XLSX y PDF, con
  reportes de resumen, ventas, pagos e impuestos.
- Las dos rutas conservan compatibilidad bajo `/api/`.
- Se agrego el estado oficial `cancelado` a los pedidos.
- Se instalaron `openpyxl` y `ReportLab` para exportaciones estructuradas.
- Se documento el contrato en `docs/API_REPORTES_COMERCIALES.md`.

Seguridad:

- Solo acceden superusuarios, administradores maestros autorizados,
  administradores de empresa y gerentes de la empresa solicitada.
- Compradores y usuarios que solicitan otra empresa reciben `403`.
- Los filtros usan limites conscientes de `America/Tegucigalpa`.
- Los valores exportados se neutralizan para evitar formulas inyectadas en
  CSV y XLSX.

Impacto para el frontend:

- El panel debe reemplazar sus calculos temporales por `resumen`, `serie`,
  `estados` y `productos_mas_vendidos`.
- Las descargas deben solicitarse como `blob` y usar el nombre recibido en
  `Content-Disposition`.
- Los montos llegan como cadenas de dos decimales y las variaciones como numero
  de un decimal o `null` cuando el periodo anterior no tiene base comparable.

Verificacion:

- 12 pruebas nuevas cubren aislamiento entre empresas, rangos, estados,
  comparacion mensual, totales, roles, formatos y rutas compatibles.
- `python manage.py test`: 171 pruebas aprobadas contra SQLite temporal, con
  correo en memoria y R2 desactivado.
- `python manage.py makemigrations --check --dry-run`: sin cambios pendientes.
- `python manage.py check`: sin problemas.

## 2026-08-06 - Pago en sucursal y prefactura por correo

Estado: implementado y verificado.

Cambios:

- Se mantuvo `POST /api/v1/pagos/iniciar/` para pago en linea y se marco su
  metodo de forma explicita en pedidos y pagos.
- Se agrego `POST /api/v1/pedidos/pedidos/{id}/pago-en-sucursal/` para crear o
  recuperar idempotentemente el pago pendiente, la sucursal y la prefactura.
- Se agrego la descarga PDF autenticada con la leyenda legal, fotografia
  comercial del pedido, sucursal, comprador, detalle, totales y vencimiento.
- Se agrego el envio inicial por Brevo al correo verificado y el reenvio con
  un limite configurable de intentos.
- Se agrego la confirmacion administrativa por referencia. Reutiliza el flujo
  comercial de pagos aprobados, valida inventario y no duplica movimientos.
- El inventario permanece intacto mientras el pago presencial esta pendiente.
- Se agrego una migracion de datos que identifica como `en_linea` los pedidos
  historicos que ya tenian pagos antes de este cambio.
- Las rutas nuevas funcionan tanto bajo `/api/v1/` como bajo `/api/`.
- Se documento el contrato en `docs/API_PAGO_EN_SUCURSAL.md` y las variables
  de prefactura en la guia de Render.

Seguridad:

- Solo el comprador propietario puede iniciar el pago, descargar desde su
  alcance y reenviar la prefactura.
- La sucursal se valida activa y dentro de la misma empresa del pedido.
- El correo destino se obtiene del perfil verificado; la API no acepta una
  direccion alternativa enviada por el cliente.
- Solo superusuarios, administradores maestros autorizados, administradores
  de empresa y gerentes de la empresa pueden confirmar pagos presenciales.
- Los querysets ocultan pedidos y pagos de empresas o compradores ajenos.

Impacto para el frontend:

- Para pago presencial debe enviar solo `sucursal_id` y aceptar `201` al crear
  o `200` al recuperar el mismo flujo.
- Debe descargar el PDF desde `prefactura.url_pdf` usando el JWT.
- El flujo existente de pago en linea no cambia de ruta ni de cuerpo.

Verificacion:

- 12 pruebas nuevas cubren permisos, aislamiento, idempotencia, PDF, correo,
  limite de reenvios, sucursal inactiva, pedido ajeno, inventario, doble
  confirmacion, pago en linea y rutas compatibles.
- `python manage.py test`: 183 pruebas aprobadas contra SQLite temporal, con
  correo en memoria y R2 desactivado.
- No se modifico Supabase, R2 ni se enviaron correos reales durante las pruebas.

Correccion posterior de integracion:

- El listado publico `GET /api/v1/empresas/sucursales/` ahora incluye el `id`
  de cada sucursal activa para que el comprador pueda enviarlo como
  `sucursal_id` al iniciar el pago presencial.
- Antes de esta correccion el frontend recibia la sucursal sin identificador y
  terminaba enviando `sucursal_id: null`, lo que producia un `400` correcto
  pero impedia completar el flujo.
- Se verificaron los identificadores reales de las sucursales activas de
  Analiza y las 72 pruebas de empresas y pagos aprobaron.
- Se corrigieron los bloqueos transaccionales del pago presencial para no
  aplicar `FOR UPDATE` sobre relaciones opcionales creadas con `LEFT JOIN`,
  operacion que PostgreSQL rechaza aunque SQLite la permita.
- El bloqueo del pedido y de la prefactura se verifico directamente contra
  Supabase. Las 12 pruebas especificas del pago presencial aprobaron y el
  intento fallido del pedido de prueba no dejo pagos, prefacturas ni movimientos
  de inventario.

## 2026-08-10 - Validaciones del registro y confirmacion de correo

Estado: implementado y verificado.

Cambios:

- El nombre completo del comprador ahora acepta exclusivamente letras Unicode
  y espacios; tambien se valida nombre y apellido en la administracion.
- El telefono acepta solo digitos en registro, perfiles y administracion.
- La identidad conserva la regla oficial de exactamente 13 digitos.
- Los nombres se normalizan eliminando espacios repetidos antes de guardarse.
- El envio de codigos exige que el backend de correo confirme exactamente un
  mensaje. Los rechazos y fallos de Brevo producen `503` y revierten la
  transaccion para no dejar cuentas o codigos inconsistentes.
- Se agrego la migracion `usuarios.0007` y se aplico en Supabase.
- Se documento el contrato y los controles del frontend en
  `docs/API_REGISTRO_COMPRADOR.md`, incluido el ojo de contrasena.

Diagnostico del correo mostrado:

- La cuenta existe inactiva y con correo pendiente de verificacion.
- Supabase registra dos codigos generados por las solicitudes del frontend;
  el segundo invalido correctamente al primero.
- La configuracion activa usa el backend SMTP, host y credenciales de Brevo.
- Una aceptacion SMTP no garantiza que Gmail coloque el mensaje en Recibidos;
  los rebotes y bloqueos posteriores se consultan en el log de Brevo.

Verificacion:

- 7 pruebas nuevas cubren nombre, telefono, identidad, registro, correo,
  reenvio y rollback cuando el proveedor no confirma.
- Las 26 pruebas de usuarios aprobaron contra SQLite temporal y correo en
  memoria, sin enviar secretos de autenticacion.
- `python manage.py test`: 190 pruebas aprobadas en la suite completa.

## 2026-08-10 - Migracion de Brevo SMTP a API HTTPS

Estado: implementado y verificado localmente.

Cambios:

- Se reemplazo el transporte SMTP por un backend de correo Django que consume
  `POST https://api.brevo.com/v3/smtp/email` mediante HTTPS.
- El cambio aplica sin modificar los servicios existentes de codigos de
  activacion, recuperacion de contrasena y prefacturas con PDF adjunto.
- El backend soporta texto, HTML, copia, copia oculta, respuesta y adjuntos en
  base64, y solo confirma el envio cuando Brevo devuelve un `messageId`.
- Las variables SMTP se retiraron de `settings.py`, `.env.example` y la
  documentacion activa. La nueva credencial obligatoria es `BREVO_API_KEY`.
- La configuracion fija el backend de API para impedir que variables SMTP
  antiguas de Render reactiven accidentalmente el transporte bloqueado.

Motivo:

- Render Free bloquea las conexiones salientes a los puertos SMTP 25, 465 y
  587. La API de Brevo usa HTTPS y mantiene el limite del plan contratado de
  Brevo sin consumir puertos SMTP.

Configuracion externa pendiente:

- Crear una clave en `Brevo > SMTP & API > API Keys` y agregarla como
  `BREVO_API_KEY` al `.env` local y a `Render > Environment`.
- Conservar `DEFAULT_FROM_EMAIL` con un remitente verificado y eliminar de
  Render `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`,
  `EMAIL_TIMEOUT`, `EMAIL_HOST_USER` y `EMAIL_HOST_PASSWORD`.
- Desplegar y probar un unico envio antes de restablecer los intentos agotados
  de una prefactura existente.

Verificacion:

- 6 pruebas del backend de correo cubren texto, HTML, PDF, autenticacion,
  errores y la integracion con `send_mail()` de Django.
- Las 196 pruebas del proyecto aprobaron contra SQLite temporal, sin consumir
  envios reales de Brevo.

## 2026-08-10 - Pagos confirmados por metodo en el resumen comercial

Estado: implementado y verificado.

Cambios:

- `GET /api/v1/reportes/resumen-ventas/` y su ruta compatible bajo `/api/`
  incluyen `resumen.pagos_por_metodo` con las claves fijas `sucursal` y
  `en_linea`.
- Solo participan pagos con estado oficial `aprobado`. Los pagos pendientes y
  rechazados se excluyen, y los pedidos pagados sin un pago confirmado no se
  atribuyen artificialmente a ningun metodo.
- Los pagos se limitan a la empresa autorizada y al rango de creacion del
  pedido en `America/Tegucigalpa`, igual que el resto del resumen.
- Cada pedido se cuenta y suma una sola vez aunque existan varios intentos o
  datos historicos duplicados. Los montos usan `Decimal` y se devuelven con dos
  decimales.
- Se confirmo mediante contrato y pruebas que el listado de pedidos incluye
  `metodo_pago` y el listado de pagos incluye `metodo`.

Verificacion:

- 3 pruebas nuevas cubren ambos metodos, valores cero, intentos duplicados,
  pagos no confirmados, aislamiento multiempresa y rango de fechas.
- Las 199 pruebas del proyecto aprobaron contra SQLite temporal.

## 2026-08-10 - Gestion administrativa de pedidos pendientes

Estado: implementado y verificado.

Cambios:

- `resumen.pendientes_por_metodo` separa pedidos pendientes entre `sucursal`,
  `en_linea` y `sin_metodo`, siempre devuelve los tres grupos y usa montos
  `Decimal` formateados con dos decimales.
- El agregado usa pedidos unicos dentro de la empresa y rango autorizados,
  conserva pedidos con intentos rechazados y excluye cualquiera con pago
  aprobado.
- Se creo `POST /api/v1/pedidos/pedidos/{id}/cancelar-pendiente/`, compatible
  tambien con `/api/`, para superusuarios y personal administrativo autorizado
  de la empresa.
- La cancelacion bloquea pagos y pedido dentro de una transaccion, cambia solo
  intentos pendientes al nuevo estado final `cancelado` y no ejecuta efectos de
  inventario.
- El pedido conserva motivo, administrador y fecha de cancelacion. Repetir la
  accion devuelve la misma auditoria con `duplicado=true`.
- Los pedidos pagados y los que tengan un pago aprobado se rechazan. La ruta
  existente `confirmar-en-sucursal` permanece como unica confirmacion
  administrativa presencial y conserva sus efectos transaccionales.
- Los listados administrativos mantienen `metodo_pago` en pedidos y exponen
  `metodo`, `estado`, `referencia`, `pedido` y `monto` en pagos.

Persistencia:

- `pedidos.0015` agrega `motivo_cancelacion`, `cancelado_por` y
  `fecha_cancelacion`.
- `pagos.0003` incorpora `cancelado` a los estados oficiales del pago.

Verificacion:

- 8 pruebas nuevas cubren separacion por metodo, intentos multiples, empresa,
  rango, permisos, idempotencia, pedidos pagados, pagos aprobados, inventario y
  compatibilidad de rutas.
- Las 207 pruebas del proyecto aprobaron contra SQLite temporal.

## 2026-08-11 - Rediseno A4 del PDF de prefactura

Estado: implementado y verificado.

Cambios:

- El PDF de `GET /api/v1/pedidos/pedidos/{id}/prefactura/pdf/` ahora usa A4
  vertical y conserva la ruta, autenticacion, `Content-Type` y nombre de archivo
  existentes.
- Logo, nombre, colores, telefono, correo, direccion y sitio web se obtienen de
  la empresa del pedido. Si el logo no esta disponible, el documento mantiene
  la marca mediante el nombre de la empresa.
- Se agregaron marca de agua repetida, datos completos de prefactura, pedido,
  sucursal y comprador, tabla comercial con descuentos, resumen de totales y
  codigo QR.
- Las tablas repiten encabezado y dividen solamente entre filas. El bloque de
  totales y cierre se conserva unido para evitar cortes entre paginas.
- Cada pagina incluye contacto de la empresa y numeracion. Las paginas
  posteriores muestran una referencia compacta de prefactura y pedido.
- El generador es determinista y es compartido por descarga y correo, por lo
  que ambos entregan exactamente el mismo PDF para los mismos datos.

Verificacion:

- 21 pruebas del flujo presencial aprobaron con SQLite temporal y aislado.
- La cobertura incluye un articulo, multiples articulos, descuentos, impuesto,
  envio, varias paginas y equivalencia binaria entre correo y descarga.
- Las 210 pruebas del proyecto aprobaron contra SQLite temporal.

Ajuste posterior:

- Se retiro por completo la marca de agua para mantener limpio el contenido.
- El logo real configurado en `empresa.logo` se conserva solo en el encabezado
  y sus margenes blancos o transparentes se recortan en memoria.
- Una prueba adicional valida logo, recorte y equivalencia entre correo y
  descarga.

## 2026-08-11 - Identidad visual compartida en reportes PDF

Estado: implementado y verificado.

Cambios:

- Los PDF de `resumen`, `ventas`, `pagos` e `impuestos` ahora usan una
  estructura visual coherente con la prefactura y no incluyen marca de agua.
- Se adopto A4 horizontal para acomodar hasta diez columnas sin perder
  legibilidad.
- El encabezado usa dinamicamente logo, nombre, colores y contacto de la
  empresa autorizada.
- Se agregaron bloques de metadata y totales, tabla con anchos calculados por
  contenido, encabezados repetidos y pie paginado.
- Se conservaron endpoint, filtros, permisos, aislamiento, tipo de contenido y
  nombre de archivo existentes.

Verificacion:

- Los cuatro tipos de PDF se validaron con identidad y estructura completa.
- Una prueba multipagina cubre continuidad del detalle y numeracion de pagina.
- Las 18 pruebas del modulo de reportes aprobaron con SQLite temporal.

Ajuste posterior:

- Se retiraron `empresa_slug` y `moneda` de JSON, CSV, XLSX y PDF.
- `empresa_slug` permanece unicamente como parametro de seleccion y seguridad.
- El slug tambien se retiro del nombre de los archivos descargados.
- Los valores numericos `0` ya no se presentan como `No registrado`.
- El detalle del reporte `resumen` ya no repite filas de estados; conserva
  solamente los productos mas vendidos debajo de los totales superiores.

## 2026-08-11 - Rediseno de reportes Excel y retiro de CSV

Estado: implementado y verificado.

Cambios:

- Los Excel ahora usan logo, colores y contacto de la empresa, con una
  estructura equivalente a la de los reportes PDF.
- Se agregaron bloques de metadata y totales, formatos numericos reales,
  autofiltro, panel congelado, filas alternas y anchos adaptativos.
- La hoja esta preparada para impresion A4 horizontal, ajustada a una pagina de
  ancho y con pie paginado.
- `csv` se retiro de formatos admitidos, exportadores y documentacion. Las
  solicitudes antiguas con `formato=csv` reciben `400 Bad Request`.

## 2026-08-11 - Filtros segmentados y reportes por sucursal y familia

Estado: implementado y verificado.

Cambios:

- El resumen y las exportaciones aceptan los filtros opcionales `ciudad`,
  `sucursal_id`, `examen_id` y `familia_id`.
- Los IDs se validan dentro de la empresa autorizada y los filtros se aplican
  tambien a series, estados, metodos de pago, productos y comparaciones.
- El resumen devuelve `filtros_aplicados` para que el frontend pueda conservar
  el estado real de la consulta.
- Se agregaron los tipos de exportacion `sucursales` y `familias` en XLSX y
  PDF. El primero ordena por compradores unicos y selecciones de pago
  presencial; el segundo agrupa ventas confirmadas e ingresos netos por
  familia sin duplicar perfiles o combos.
- `SucursalEmpresa` incorpora el campo estructurado `ciudad`, visible en API y
  administracion. Su listado admite filtro, busqueda y orden por ciudad.
- El Excel ahora presenta todos los filtros aplicados, incluso cuando ocupan
  mas de una fila de metadata.

Persistencia:

- `empresas.0017` agrega `SucursalEmpresa.ciudad` sin inferir datos desde la
  direccion libre. Las sucursales existentes deben completar este campo.

Ajuste posterior:

- El reporte `familias` dejo de consolidar una fila por familia. Ahora lista
  cada producto o examen de la familia seleccionada, incluidos los que no
  tuvieron ventas, con sus pedidos, unidades e ingresos directos.

Verificacion:

- Las 22 pruebas del modulo de reportes aprobaron contra SQLite temporal.
- Se comprobaron filtros, aislamiento multiempresa, IDs incompatibles,
  personas unicas, selecciones repetidas, ventas confirmadas, XLSX, PDF y rutas
  `/api/` y `/api/v1/`.
- `makemigrations --check --dry-run`, compilacion y la prueba publica de
  sucursales finalizaron correctamente.
