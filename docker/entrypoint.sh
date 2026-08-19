#!/bin/sh
set -eu

es_verdadero() {
    case "${1:-}" in
        1|true|TRUE|yes|YES|si|SI) return 0 ;;
        *) return 1 ;;
    esac
}

if es_verdadero "${DJANGO_COLLECTSTATIC:-true}"; then
    python manage.py collectstatic --noinput
fi

if es_verdadero "${DJANGO_RUN_MIGRATIONS:-false}"; then
    python manage.py migrate --noinput
fi

if es_verdadero "${DJANGO_ENSURE_SUPERUSER:-false}"; then
    python manage.py asegurar_superusuario
fi

if [ "${1:-}" = "web" ]; then
    shift
    set -- gunicorn config.wsgi:application \
        --bind "0.0.0.0:${PORT:-8000}" \
        --workers "${GUNICORN_WORKERS:-2}" \
        --threads "${GUNICORN_THREADS:-2}" \
        --timeout "${GUNICORN_TIMEOUT:-120}" \
        --graceful-timeout "${GUNICORN_GRACEFUL_TIMEOUT:-30}" \
        --max-requests "${GUNICORN_MAX_REQUESTS:-1000}" \
        --max-requests-jitter "${GUNICORN_MAX_REQUESTS_JITTER:-100}" \
        --access-logfile - \
        --error-logfile - \
        "$@"
fi

exec "$@"
