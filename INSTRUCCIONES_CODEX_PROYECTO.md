# INSTRUCCIONES PARA CODEX
## Proyecto: Sistema web de ventas en línea multiempresa

Estas instrucciones deben seguirse durante todo el desarrollo del proyecto. No deben omitirse, reinterpretarse ni reemplazarse sin autorización expresa del usuario.

---

# 1. Regla principal de trabajo

Antes de realizar cualquier acción, debes preguntarme qué deseo hacer y esperar mi autorización.

No debes:

- crear archivos;
- modificar archivos existentes;
- eliminar archivos;
- mover o renombrar archivos;
- instalar dependencias;
- ejecutar comandos;
- crear migraciones;
- aplicar migraciones;
- modificar la base de datos;
- crear tablas;
- cambiar configuraciones;
- hacer commits;
- hacer push;
- desplegar en Vercel o Render;
- configurar PayPal;
- enviar correos;
- configurar WhatsApp;
- crear usuarios;
- cambiar permisos;
- alterar el diseño;
- tomar decisiones técnicas definitivas;

sin pedirme permiso primero.

Aunque una acción parezca necesaria, sencilla, automática o recomendable, debes explicármela y preguntarme antes de ejecutarla.

## Forma obligatoria de pedir autorización

Antes de actuar, responde con esta estructura:

1. **Qué entendí:** explica brevemente lo que solicitaste.
2. **Qué propongo hacer:** detalla los archivos, comandos o cambios necesarios.
3. **Opciones disponibles:** presenta alternativas cuando existan.
4. **Riesgos o consecuencias:** indica si algo puede afectar datos, diseño, seguridad o funcionamiento.
5. **Confirmación:** pregunta claramente: **¿Autorizas que lo haga de esta manera?**

Solo debes continuar cuando yo responda de forma clara que sí autorizo.

Una aprobación para una acción no significa aprobación para acciones posteriores. Debes volver a preguntar antes de pasar a otra etapa importante.

---

# 2. Forma de trabajar conmigo

Debes trabajar de forma guiada y paso a paso.

- No debes adelantarte.
- No debes completar funciones que no te haya pedido.
- No debes asumir preferencias.
- No debes elegir colores, estructuras, nombres, bibliotecas o componentes sin consultarme.
- No debes cambiar algo que ya aprobé sin preguntarme.
- No debes reemplazar mis decisiones por recomendaciones tuyas.
- Puedes sugerir mejoras, pero deben presentarse como opciones, no como cambios automáticos.
- Cuando haya varias formas de hacer algo, debes explicarlas de manera sencilla y dejarme escoger.
- Debes respetar exactamente la forma en que yo quiera organizar el proyecto.
- Debes conservar una lista de decisiones aprobadas para no contradecirlas después.

Si una instrucción mía no está clara, debes hacer preguntas antes de tocar el proyecto.

---

# 3. Regla para el código

Antes de escribir código, debes mostrarme:

- el objetivo del cambio;
- los archivos que piensas crear o modificar;
- la estructura propuesta;
- la lógica principal;
- las dependencias necesarias;
- cualquier cambio en la base de datos;
- cualquier implicación de seguridad;
- una explicación breve de cómo se probará.

Después debes esperar mi autorización.

Cuando autorice el cambio:

- realiza únicamente lo aprobado;
- no agregues funciones adicionales;
- no refactorices partes no relacionadas;
- no cambies nombres que ya fueron aprobados;
- no elimines código sin permiso;
- no modifiques el diseño visual sin permiso;
- informa exactamente qué cambiaste;
- muestra los archivos afectados;
- indica cómo puedo probarlo.

---

# 4. Tecnologías aprobadas

El proyecto utilizará inicialmente:

- **Frontend:** React.
- **Backend:** Django.
- **Comunicación:** API REST.
- **Base de datos:** Supabase.
- **Almacenamiento de imágenes:** almacenamiento en línea vinculado al proyecto.
- **Frontend en producción:** Vercel.
- **Backend en producción:** Render.
- **Pasarela de pago inicial:** PayPal.
- **Pasarela futura:** BAC o Cuscatlán, únicamente en una fase posterior y con autorización.

No debes sustituir estas tecnologías sin consultarme.

No debes instalar paquetes, crear proyectos, configurar variables de entorno ni conectar servicios sin autorización previa.

---

# 5. Tipo de aplicación

El sistema será una **aplicación web**, pensada principalmente para utilizarse desde navegadores de computadora.

Puede ser adaptable a diferentes tamaños de pantalla, pero no debe tratarse como una aplicación móvil nativa.

El diseño debe mantenerse:

- sobrio;
- formal;
- limpio;
- fácil de entender;
- con textos principalmente en color negro;
- utilizando los colores corporativos solo como acentos visuales;
- sin exceso de colores en títulos o párrafos.

No debes cambiar el diseño aprobado sin pedirme permiso.

---

# 6. Identidad visual inicial

La empresa de referencia inicial es **Analiza Laboratorios Clínicos**.

La identidad visual utiliza principalmente:

- rojo oscuro: `#d1393d`;
- rojo claro: `#e94a51`;
- azul: `#2d4b77`;
- gris: `#6e6f70`;
- blanco como fondo principal;
- negro para la mayor parte del texto.

El encabezado de la página web debe conservar como referencia:

- logotipo de Analiza;
- nombre de la empresa;
- buscador en la parte superior;
- menú principal;
- favoritos;
- carrito;
- acceso a la cuenta del usuario.

No debe duplicarse el acceso a “Mi cuenta” en diferentes partes de la misma vista.

El carrito debe permanecer oculto mientras no esté seleccionado y mostrarse como panel desplegable cuando el usuario haga clic en él.

---

# 7. Arquitectura multiempresa

El sistema debe diseñarse desde el inicio para trabajar en modalidad multiempresa o multi-tenant.

Una sola plataforma debe poder administrar varias empresas sin mezclar su información.

Cada empresa tendrá sus propios datos, entre ellos:

- nombre;
- logotipo;
- colores básicos;
- usuarios;
- clientes;
- productos;
- familias;
- categorías;
- inventario;
- promociones;
- pedidos;
- ventas;
- reportes;
- tarifas de envío;
- configuración general.

Cuando un usuario inicie sesión, el sistema debe identificar a qué empresa pertenece y consultar únicamente la información de esa empresa.

## Reglas obligatorias de aislamiento

- Todos los registros que correspondan deben estar relacionados con una empresa.
- Un usuario no debe acceder a los datos de otra empresa.
- Los administradores de una empresa no deben ver información de otra empresa.
- Las consultas del backend deben filtrar por empresa.
- Las APIs deben validar la empresa del usuario autenticado.
- No debes implementar una estrategia multiempresa definitiva sin mostrarme primero las opciones y pedirme autorización.

Antes de crear el modelo multiempresa, debes explicarme al menos estas opciones:

1. una sola base de datos con campo `empresa_id`;
2. esquemas separados;
3. bases de datos separadas.

Debes recomendar una opción, explicar ventajas y desventajas y esperar mi decisión.

---

# 8. Niveles de usuario

El sistema tendrá tres niveles principales.

## 8.1 Administrador maestro

Podrá:

- administrar empresas;
- administrar usuarios;
- asignar roles y permisos;
- bloquear o eliminar usuarios;
- controlar productos;
- controlar promociones;
- controlar inventario;
- revisar pedidos;
- ver paneles y reportes;
- configurar el impuesto;
- configurar tarifas de envío;
- revisar movimientos y acciones realizadas.

Debes preguntarme antes de definir exactamente qué permisos tendrá cada rol.

## 8.2 Gerentes

Podrán, según los permisos que yo apruebe:

- agregar productos;
- editar productos;
- asignar familia y categoría;
- registrar precio;
- registrar una imagen principal;
- registrar código de barras;
- actualizar inventario;
- revisar pedidos;
- actualizar el estado de pedidos;
- activar promociones;
- ver ventas del día;
- ver productos con poca existencia;
- crear usuarios internos, únicamente si el administrador lo permite.

## 8.3 Compradores

Podrán:

- crear su cuenta;
- verificar su correo;
- iniciar sesión;
- recuperar su contraseña;
- consultar el catálogo;
- buscar productos;
- filtrar productos;
- agregar productos al carrito;
- seleccionar forma de entrega;
- pagar en línea;
- consultar pedidos;
- descargar una prefactura;
- actualizar sus datos personales.

---

# 9. Registro y verificación de clientes

Para comprar, el cliente deberá registrarse.

Datos iniciales previstos:

- nombre completo;
- correo electrónico;
- número de teléfono;
- contraseña;
- confirmación de contraseña;
- aceptación de términos y condiciones;
- aceptación de política de privacidad.

Después del registro:

1. el sistema enviará un código al correo electrónico;
2. el usuario deberá ingresar el código;
3. el código tendrá vigencia limitada;
4. el código se utilizará una sola vez;
5. el usuario no podrá comprar hasta verificar el correo.

Antes de implementar el envío de correos, debes preguntarme qué proveedor y qué cuenta se utilizarán.

---

# 10. Recuperación de contraseña

No se enviará una contraseña genérica.

El proceso será:

1. el usuario ingresa su correo;
2. el sistema genera un código temporal;
3. el código se envía al correo;
4. el usuario verifica el código;
5. el usuario crea una nueva contraseña;
6. la contraseña anterior deja de funcionar;
7. se envía una confirmación del cambio.

Debes preguntarme antes de definir:

- duración del código;
- cantidad de intentos;
- tiempo para solicitar otro código;
- reglas de complejidad de contraseña.

---

# 11. Catálogo de productos

Cada producto tendrá inicialmente:

- identificador interno autoincrementable;
- código de barras único;
- nombre;
- descripción;
- una sola imagen principal;
- precio;
- existencia;
- familia;
- categoría;
- estado;
- información de descuento cuando aplique;
- empresa a la que pertenece.

El identificador interno no se mostrará al cliente.

Los productos podrán buscarse por:

- nombre;
- código de barras;
- familia;
- categoría.

No debes agregar imágenes adicionales ni variantes de producto sin consultarme.

---

# 12. Familias y categorías

Los productos estarán organizados por familias y categorías.

Antes de crear los modelos debes preguntarme:

- si una categoría pertenece a una sola familia;
- si un producto puede pertenecer a más de una categoría;
- si las familias y categorías pueden desactivarse;
- si pueden ordenarse manualmente;
- si se permitirá eliminarlas cuando tengan productos relacionados.

---

# 13. Promociones y descuentos

El administrador o gerente autorizado podrá:

- crear descuentos;
- seleccionar uno o varios productos;
- definir porcentaje o monto;
- establecer fecha de inicio;
- establecer fecha de finalización;
- activar o desactivar la promoción.

En el catálogo, un producto con descuento podrá mostrar:

- una cinta o distintivo visual;
- precio anterior;
- precio con descuento;
- porcentaje de descuento.

Los productos en promoción podrán aparecer en un carrusel o sección destacada.

En el carrito debe mostrarse el descuento total aplicado.

Antes de implementar descuentos debes preguntarme:

- si serán por porcentaje o valor fijo;
- si podrán combinarse;
- si habrá prioridad entre promociones;
- si el impuesto se calcula antes o después del descuento;
- qué ocurre cuando una promoción vence mientras el producto está en el carrito.

---

# 14. Carrito de compras

El carrito deberá:

- estar oculto por defecto;
- abrirse cuando el usuario seleccione el icono;
- mostrar la cantidad de productos agregados;
- permitir aumentar cantidades;
- permitir disminuir cantidades;
- permitir eliminar productos;
- validar la existencia disponible;
- mostrar nombre, imagen, precio y cantidad;
- mostrar subtotal;
- mostrar descuento total;
- mostrar impuesto;
- mostrar costo de envío;
- mostrar gran total.

El impuesto será inicialmente del **15 %**.

La moneda será **lempiras**.

Fórmula inicial:

`Gran total = subtotal - descuentos + impuesto + envío`

Antes de programar la fórmula definitiva debes confirmar conmigo el orden exacto del cálculo.

---

# 15. Opciones de entrega

El cliente podrá seleccionar:

## Tegucigalpa

- se solicitará dirección;
- tendrá una tarifa local;
- tiempo estimado: un día.

## Envío nacional

- se solicitará dirección completa;
- tendrá una tarifa nacional;
- tiempo estimado: de dos a cuatro días.

## Retiro en local

- no tendrá costo de envío;
- no será obligatoria una dirección;
- se mostrará la dirección del local;
- el cliente podrá retirar cuando el pedido esté listo.

Las tarifas deben quedar configurables desde el panel administrativo.

Antes de crear los campos de dirección debes preguntarme exactamente qué información se solicitará para Tegucigalpa y para envíos nacionales.

---

# 16. Pasarela de pago

La primera pasarela será PayPal.

Inicialmente se contemplarán:

- tarjetas de crédito;
- tarjetas de débito, siempre que PayPal y la región lo permitan.

El sistema no debe almacenar datos completos de tarjetas.

Cada transacción deberá registrar, como mínimo:

- pedido;
- cliente;
- empresa;
- fecha y hora;
- monto;
- moneda;
- proveedor;
- referencia de la transacción;
- estado;
- respuesta necesaria de la pasarela.

Estados previstos:

- pendiente;
- aprobado;
- rechazado;
- fallido;
- reembolsado, cuando corresponda.

No debes configurar PayPal, crear credenciales, usar modo sandbox ni implementar webhooks sin pedirme permiso.

---

# 17. Pedidos

Cada compra generará un pedido único.

Estados iniciales posibles:

- pago pendiente;
- pago aprobado;
- en preparación;
- listo para retirar;
- listo para despacho;
- enviado;
- entregado;
- cambio solicitado;
- cambio aprobado;
- cambio rechazado.

Los pedidos pagados no podrán cancelarse.

Los cambios únicamente aplicarán cuando el producto se encuentre en mal estado.

Antes de implementar los estados debes preguntarme cuáles se usarán finalmente y qué rol puede cambiar cada uno.

---

# 18. Inventario

El sistema deberá:

- registrar entradas;
- registrar salidas;
- registrar ajustes;
- descontar existencia después de una compra aprobada;
- impedir ventas mayores a la existencia;
- mostrar productos agotados;
- mostrar alertas de inventario bajo;
- registrar el usuario que realizó cada movimiento;
- relacionar cada movimiento con su empresa.

Antes de implementar inventario debes preguntarme:

- cuándo se reserva una unidad;
- cuándo se descuenta definitivamente;
- qué ocurre si el pago falla;
- si se permitirá inventario negativo;
- cuál será el nivel mínimo de alerta;
- si habrá varias sucursales o bodegas.

---

# 19. Prefactura

Después del pago aprobado se generará una prefactura, no una factura fiscal original.

Debe incluir:

- nombre de la empresa;
- datos de contacto;
- número de pedido;
- número de prefactura;
- fecha y hora;
- datos del cliente;
- tipo de entrega;
- dirección cuando corresponda;
- productos;
- cantidades;
- precios;
- subtotal;
- descuentos;
- impuesto del 15 %;
- envío;
- total;
- método de pago;
- estado del pago.

Debe mostrar la leyenda:

**“Este documento corresponde a una prefactura y no representa una factura fiscal original”.**

Antes de generar PDF o diseño de prefactura debes mostrarme una propuesta y esperar autorización.

---

# 20. Notificaciones de venta

Cuando una compra sea aprobada, el personal de ventas debe recibir una notificación.

Posibles medios:

- correo electrónico;
- WhatsApp mediante integración autorizada;
- notificación interna.

La notificación podrá incluir:

- número de pedido;
- cliente;
- teléfono;
- productos;
- cantidades;
- total;
- tipo de entrega;
- dirección;
- estado del pago;
- fecha y hora.

No debes implementar WhatsApp ni correo sin preguntarme cuál medio se utilizará primero.

---

# 21. Paneles y reportes

El sistema podrá mostrar:

- ventas del día;
- ventas semanales y mensuales;
- pedidos por estado;
- ingresos;
- productos más vendidos;
- productos con inventario bajo;
- productos agotados;
- promociones activas;
- clientes registrados;
- ventas por familia;
- ventas por categoría;
- impuesto recaudado;
- descuentos aplicados;
- ingresos por envío;
- ventas por tipo de entrega.

No debes crear todos los paneles de una vez. Debes preguntarme cuál se desarrollará primero.

---

# 22. Diseño de la página principal

La página principal web tendrá como referencia:

- logotipo y nombre de Analiza en la parte superior;
- buscador superior visible;
- menú de navegación;
- acceso a favoritos;
- icono del carrito;
- acceso a la cuenta en un solo lugar;
- banner de promoción;
- categorías;
- exámenes o servicios destacados;
- botones para agregar al carrito.

El carrito no debe permanecer abierto todo el tiempo. Solo debe aparecer al seleccionarlo.

No debe incluir una sección de citas, porque esta función no forma parte del alcance aprobado.

No debes agregar nuevas secciones visuales sin autorización.

---

# 23. Seguridad

El sistema deberá contemplar:

- contraseñas cifradas;
- autenticación segura;
- control de acceso por rol;
- validación de permisos por empresa;
- validación de formularios;
- protección contra accesos no autorizados;
- validación del inventario;
- protección de datos personales;
- registros de actividades administrativas cuando se aprueben.

No debes afirmar que el sistema es seguro solo por funcionar. Debes explicar cada medida antes de implementarla.

---

# 24. Proceso de desarrollo obligatorio

El trabajo debe dividirse en fases. Antes de iniciar cada fase debes mostrarme el alcance y esperar autorización.

## Fase 1: revisión y planificación

- revisar estructura existente;
- detectar archivos actuales;
- proponer arquitectura;
- proponer estructura de carpetas;
- proponer modelo multiempresa;
- definir módulos.

No modificar nada en esta fase sin permiso.

## Fase 2: configuración inicial

- React;
- Django;
- API REST;
- conexión con Supabase;
- variables de entorno.

Preguntar antes de crear o instalar cualquier cosa.

## Fase 3: autenticación y empresas

- empresas;
- usuarios;
- roles;
- permisos;
- registro;
- verificación;
- recuperación de contraseña.

## Fase 4: catálogo e inventario

- familias;
- categorías;
- productos;
- imágenes;
- código de barras;
- inventario.

## Fase 5: interfaz pública

- encabezado;
- buscador;
- menú;
- catálogo;
- promociones;
- favoritos;
- carrito ocultable.

## Fase 6: proceso de compra

- carrito;
- entrega;
- dirección;
- impuesto;
- descuentos;
- totales.

## Fase 7: pagos

- PayPal;
- confirmación;
- webhook;
- estados del pago.

## Fase 8: pedidos y prefactura

- registro del pedido;
- actualización del inventario;
- prefactura;
- notificaciones.

## Fase 9: paneles y reportes

- seleccionar conmigo cuáles se implementan primero.

## Fase 10: pruebas y despliegue

- pruebas;
- correcciones;
- Vercel;
- Render;
- configuración final.

No desplegar sin permiso explícito.

---

# 25. Pruebas

Antes de ejecutar pruebas debes decirme:

- qué se probará;
- qué comandos se ejecutarán;
- si se crearán datos de prueba;
- si se modificará la base de datos;
- cuánto tiempo puede tardar;
- qué resultado se espera.

No debes borrar datos de prueba ni limpiar la base de datos sin preguntarme.

---

# 26. Comandos y terminal

Antes de ejecutar un comando debes mostrarme el comando exacto y explicar para qué sirve.

No debes ejecutar comandos destructivos o de alto riesgo, incluyendo, entre otros:

- `rm`;
- `rmdir`;
- `del`;
- `drop`;
- `truncate`;
- `reset --hard`;
- `clean`;
- eliminación de migraciones;
- sobrescritura de archivos;
- eliminación de ramas;
- eliminación de bases de datos;

sin una autorización específica para ese comando.

---

# 27. Git y control de versiones

No debes:

- inicializar Git;
- crear ramas;
- hacer commit;
- hacer push;
- hacer pull;
- hacer merge;
- resolver conflictos;
- cambiar el remoto;
- borrar historial;

sin preguntarme primero.

Antes de un commit debes mostrarme:

- los archivos modificados;
- un resumen de cambios;
- el mensaje de commit propuesto.

---

# 28. Variables de entorno y secretos

Nunca debes escribir credenciales reales directamente en el código.

Debes usar variables de entorno para:

- Supabase;
- PayPal;
- correo;
- claves secretas de Django;
- servicios externos;
- credenciales de despliegue.

No debes mostrar secretos en respuestas, logs, commits o archivos públicos.

Antes de crear o modificar un archivo `.env`, debes pedirme permiso.

---

# 29. Formato de cada respuesta de Codex

Mientras trabajemos en este proyecto, responde con este formato:

## Entendí

Resume lo que te pedí.

## Antes de hacerlo necesito confirmar

Haz las preguntas necesarias.

## Propuesta

Explica lo que sugieres hacer.

## Archivos o comandos que se afectarían

Enumera cada archivo y comando.

## Opciones

Presenta alternativas cuando existan.

## Esperando autorización

Finaliza con:

**No realizaré ningún cambio hasta que me confirmes cómo deseas continuar.**

---

# 30. Instrucción final permanente

Tu función es ayudarme a desarrollar el proyecto según mis decisiones.

No tienes autorización general para actuar por tu cuenta.

Debes consultar antes de cada cambio importante y respetar exactamente la opción que yo elija.

Cuando algo no esté definido, debes preguntarme.

Cuando creas que existe una mejor alternativa, puedes explicarla, pero no debes implementarla sin permiso.

Cuando yo apruebe una tarea, realiza únicamente esa tarea y después detente para mostrarme el resultado y preguntarme cuál será el siguiente paso.
