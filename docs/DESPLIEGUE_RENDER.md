# Despliegue temporal en Render

## Comandos del servicio

Configurar en Render:

```text
Build Command: bash build.sh
Start Command: bash start.sh
```

`start.sh` ejecuta, en orden:

1. `python manage.py migrate --noinput`.
2. `python manage.py asegurar_superusuario`.
3. Gunicorn en `0.0.0.0:$PORT`.

## Superusuario sin Render Shell

Crear estas variables exclusivamente en `Render > Environment`:

```env
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=correo-administrativo@example.com
DJANGO_SUPERUSER_PASSWORD=UNA_CONTRASENA_SEGURA
```

Reglas:

- No escribir la contrasena real en Git, `.env.example` ni documentos.
- La contrasena debe superar los validadores de seguridad de Django.
- El comando crea el usuario si no existe y lo actualiza sin duplicarlo si ya
  existe.
- El usuario queda activo, con acceso a Django Admin, perfil de administrador
  maestro y correo verificado.
- Si falta una variable o la contrasena es debil, el inicio falla mostrando un
  mensaje claro en los logs de Render.

## Variables requeridas

`settings.py` no contiene valores ambientales de respaldo. Todas estas claves
deben existir en `Render > Environment` antes de desplegar:

```env
SECRET_KEY=VALOR_SEGURO_GENERADO_EN_RENDER
DJANGO_DEBUG=False
ALLOWED_HOSTS=sistema-de-ventas-backend.onrender.com
CORS_ALLOWED_ORIGINS=https://sistema-de-ventas-frontend-sandy.vercel.app
CSRF_TRUSTED_ORIGINS=https://sistema-de-ventas-frontend-sandy.vercel.app
CORS_ALLOW_CREDENTIALS=True
DATABASE_URL=postgresql://USUARIO:CONTRASENA@HOST_POOLER:5432/postgres?sslmode=require
DATABASE_CONN_MAX_AGE=0
R2_STORAGE_ENABLED=True
R2_ACCESS_KEY_ID=CLAVE_DE_ACCESO_R2
R2_SECRET_ACCESS_KEY=CLAVE_SECRETA_R2
R2_BUCKET_NAME=sistema-ventas-media
R2_ENDPOINT_URL=https://ACCOUNT_ID.r2.cloudflarestorage.com
R2_PUBLIC_BASE_URL=https://URL_PUBLICA.r2.dev
R2_REGION_NAME=auto
JWT_ACCESS_TOKEN_MINUTES=15
JWT_SESSION_MAX_HOURS=5
JWT_REFRESH_COOKIE_NAME=ventas_refresh
JWT_REFRESH_COOKIE_SECURE=True
JWT_REFRESH_COOKIE_SAMESITE=None
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp-relay.brevo.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_TIMEOUT=10
EMAIL_HOST_USER=USUARIO_SMTP_DE_BREVO
EMAIL_HOST_PASSWORD=CLAVE_SMTP_DE_BREVO
DEFAULT_FROM_EMAIL=Sistema de Ventas <REMITENTE_VERIFICADO_EN_BREVO>
PAGOS_PROVEEDOR_DEFAULT=simulado
PREFACTURA_VIGENCIA_HORAS=48
PREFACTURA_MAX_INTENTOS_CORREO=4
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=correo-administrativo@example.com
DJANGO_SUPERUSER_PASSWORD=UNA_CONTRASENA_SEGURA
```

No incluir `/` al final de los origenes o dominios.

`CORS_ALLOWED_ORIGIN_REGEXES` y `PAGOS_WEBHOOK_SECRET` son opcionales mientras
se usan origenes CORS exactos y pagos simulados. `EMAIL_HOST_USER` y
`EMAIL_HOST_PASSWORD` son obligatorios cuando se activa el backend SMTP.

En Brevo, `EMAIL_HOST_USER` es el inicio de sesion SMTP y
`EMAIL_HOST_PASSWORD` es una clave SMTP, no la contrasena de la cuenta ni una
clave de API. El correo incluido en `DEFAULT_FROM_EMAIL` debe existir como
remitente verificado en Brevo. Guardar estos valores solamente en
`Render > Environment` y en el `.env` local ignorado por Git.

`PREFACTURA_VIGENCIA_HORAS` define por cuanto tiempo puede presentarse una
prefactura para pago en sucursal. `PREFACTURA_MAX_INTENTOS_CORREO` incluye el
envio inicial y los reenvios solicitados por el comprador.

Las variables `R2_*` son obligatorias cuando `R2_STORAGE_ENABLED=True`. Las
credenciales deben pertenecer a un token limitado al bucket de medios.

Render entrega estas claves como variables reales del proceso. En desarrollo,
`python-decouple` obtiene los mismos nombres desde el archivo `.env`, que no se
sube a Git.

## Persistencia

- Render usa Supabase PostgreSQL mediante `DATABASE_URL` para los datos.
- `DATABASE_CONN_MAX_AGE=0` libera la conexion al terminar cada solicitud y
  evita agotar el limite del Session pooler de Supabase.
- Las imagenes usan Cloudflare R2 cuando `R2_STORAGE_ENABLED=True`.
- No se depende del disco efimero de Render para datos ni archivos cargados.
- Durante pruebas se permite `r2.dev`; para produccion se configurara un
  dominio personalizado de medios.
