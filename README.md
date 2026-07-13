# Sistema web de ventas en linea - Backend

Backend inicial en Django para el sistema web de ventas en linea multiempresa.

## Entorno local

```powershell
.\.venv\Scripts\activate
python manage.py runserver
```

## Dependencias principales

- Django
- Django REST Framework
- django-cors-headers
- psycopg para PostgreSQL/Supabase
- python-decouple
- dj-database-url
- gunicorn
- whitenoise
- Pillow

## Notas

- La configuracion usa `.env` para valores locales.
- Supabase se conectara despues usando `DATABASE_URL`, cuando se aprueben las credenciales.
- No se ejecutaron migraciones ni se modifico ninguna base de datos en esta preparacion.
