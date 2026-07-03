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

echo "[entrypoint] Starting application: $*"
exec "$@"
