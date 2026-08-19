FROM python:3.11.9-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

RUN addgroup --system --gid 10001 django \
    && adduser --system --uid 10001 --ingroup django --home /home/django django

COPY requirements.txt ./
RUN python -m pip install --requirement requirements.txt

COPY --chown=django:django . .
RUN chmod 0755 /app/docker/entrypoint.sh \
    && mkdir -p /app/staticfiles /app/media \
    && chown -R django:django /app/staticfiles /app/media

USER django

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import os, urllib.request; port = os.getenv('PORT', '8000'); request = urllib.request.Request(f'http://127.0.0.1:{port}/health/', headers={'Host': os.getenv('DOCKER_HEALTHCHECK_HOST', 'localhost')}); urllib.request.urlopen(request, timeout=3).read()"

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["web"]
