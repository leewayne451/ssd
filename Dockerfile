# syntax=docker/dockerfile:1
#
# Château Collective — application image
# Runs the Flask app under Gunicorn as an unprivileged user.
# nginx (TLS termination / reverse proxy) runs as a separate service; see
# docker-compose.yml.

FROM python:3.12-slim-bookworm AS base

# Runtime hygiene: no .pyc files, unbuffered stdout/stderr (so `docker logs`
# shows output immediately), no pip cache in the image layer.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    FLASK_APP=wsgi.py

# Create an unprivileged system user — the app never runs as root.
RUN groupadd --system app \
    && useradd --system --gid app --home-dir /app --shell /usr/sbin/nologin app

WORKDIR /app

# Install runtime dependencies first so this layer caches unless requirements
# change (keeps rebuilds fast).
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Copy the application source (respecting .dockerignore).
COPY . .

# Ensure the entrypoint is executable regardless of the host's file mode
# (Windows checkouts don't preserve the +x bit).
RUN chmod +x /app/docker-entrypoint.sh

# Writable runtime directories. These are mounted as named volumes in
# docker-compose.yml; creating + chowning them here means the volumes inherit
# the correct (non-root) ownership on first use.
RUN mkdir -p /app/instance /app/uploads /app/logs \
    && chown -R app:app /app

# Drop root.
USER app

EXPOSE 8000

# Container-level liveness probe against the app's existing /healthz route.
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
    CMD python -c "import sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2).status == 200 else 1)"

# Entrypoint applies DB migrations, then exec's the CMD (Gunicorn).
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["gunicorn", "-c", "deploy/gunicorn/gunicorn.conf.py", "wsgi:app"]
