#!/usr/bin/env bash
set -o errexit

python manage.py migrate --noinput
python manage.py asegurar_superusuario
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}"
