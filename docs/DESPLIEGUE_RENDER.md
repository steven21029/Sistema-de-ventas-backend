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

## Variables web minimas

```env
SECRET_KEY=VALOR_SEGURO_GENERADO_EN_RENDER
DJANGO_DEBUG=False
ALLOWED_HOSTS=sistema-de-ventas-backend.onrender.com
CORS_ALLOWED_ORIGINS=https://sistema-de-ventas-frontend-sandy.vercel.app
CSRF_TRUSTED_ORIGINS=https://sistema-de-ventas-frontend-sandy.vercel.app
JWT_REFRESH_COOKIE_SECURE=True
JWT_REFRESH_COOKIE_SAMESITE=None
```

No incluir `/` al final de los origenes o dominios.

## Limitacion actual

Mientras no se configure `DATABASE_URL`, Render usa SQLite en almacenamiento
efimero. El superusuario se vuelve a asegurar en cada arranque, pero empresas,
productos y demas datos pueden perderse en reinicios o nuevos despliegues.
