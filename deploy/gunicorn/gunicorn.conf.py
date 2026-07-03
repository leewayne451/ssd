"""Gunicorn configuration for Château Collective (containerized).

Loaded via `gunicorn -c deploy/gunicorn/gunicorn.conf.py wsgi:app`.
"""
import os

# Bind on all interfaces *inside the container*. Port 8000 is never published to
# the host (see docker-compose.yml) — only the nginx service reaches it over the
# private compose network.
bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:8000")

# Worker count. NOTE: the app uses SQLite, which serializes writes, so a large
# worker pool mostly adds write-lock contention rather than throughput. A small
# pool is the right default here; raise it (or move to Postgres) if needed.
workers = int(os.environ.get("GUNICORN_WORKERS", "3"))
worker_class = "sync"

# Recycle workers periodically to bound any slow memory growth.
max_requests = 1000
max_requests_jitter = 100

timeout = 30
graceful_timeout = 30
keepalive = 5

# Heartbeat file on tmpfs avoids stalls if the container disk is slow.
worker_tmp_dir = "/dev/shm"

# Log to stdout/stderr so `docker logs` / compose capture everything.
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOGLEVEL", "info")
