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
- openpyxl para reportes XLSX
- ReportLab para reportes PDF

## Documentacion de API

- `docs/API_PANEL_ADMINISTRATIVO.md`: contrato general del panel.
- `docs/API_REPORTES_COMERCIALES.md`: resumen y exportacion de ventas.
- `docs/API_PAGO_EN_SUCURSAL.md`: pago presencial, prefactura y confirmacion.

## Notas

- La configuracion usa `.env` para valores locales.
- Supabase se conectara despues usando `DATABASE_URL`, cuando se aprueben las credenciales.
- No se ejecutaron migraciones ni se modifico ninguna base de datos en esta preparacion.
