#!/usr/bin/env sh
# Château Collective — container entrypoint.
# 1) Apply database migrations (idempotent — safe on every start).
# 2) exec the CMD (Gunicorn) so it becomes PID 1 and receives signals cleanly.
set -eu

export FLASK_APP="${FLASK_APP:-wsgi.py}"

echo "[entrypoint] Applying database migrations (flask db upgrade)…"
if ! flask db upgrade; then
    echo "[entrypoint] ERROR: 'flask db upgrade' failed." >&2
    echo "[entrypoint] Check that migrations/ is present and DATABASE_URL is reachable." >&2
    exit 1
fi

# 1b) Ensure the bootstrap admin exists (idempotent; explicit no-op unless
#     BOTH ADMIN_EMAIL and ADMIN_PASSWORD are set — see app/cli.py).
echo "[entrypoint] Ensuring bootstrap admin (flask seed-admin)…"
if ! flask seed-admin; then
    echo "[entrypoint] ERROR: 'flask seed-admin' failed." >&2
    echo "[entrypoint] Check ADMIN_EMAIL/ADMIN_PASSWORD in the .env next to docker-compose.yml." >&2
    exit 1
fi

echo "[entrypoint] Starting application: $*"
exec "$@"
