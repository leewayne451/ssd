#!/usr/bin/env bash
# Château Collective — SQLite backup script (runs on the AWS VM host)
#
# Satisfies D1: FSR-25 (backup), NFSR-11 (recovery availability),
# SDR-10 (backup/restore testing — see deploy/scripts/README.md for the
# documented restore procedure).
#
# What it does:
#   1. Uses SQLite's online .backup API *inside* the running web container
#      (safe against mid-write corruption — never copies a live DB file raw).
#   2. Copies the snapshot out to ~/backups/chateau/ with a UTC timestamp.
#   3. Writes a SHA-256 checksum next to it (integrity / tamper-evidence).
#   4. Prunes backups older than RETENTION_DAYS.
#
# Install as a daily cron job (03:00) with:
#   crontab -e
#   0 3 * * * /home/student31/ssd/deploy/scripts/backup.sh >> /home/student31/backups/backup.log 2>&1

set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/ssd}"
BACKUP_DIR="${BACKUP_DIR:-$HOME/backups/chateau}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$BACKUP_DIR/chateau-$STAMP.db"

mkdir -p "$BACKUP_DIR"
cd "$REPO_DIR"

echo "[backup] $STAMP — creating consistent snapshot inside the container"
docker compose exec -T web python - <<'PY'
import sqlite3
src = sqlite3.connect("/app/instance/chateau.db")
dst = sqlite3.connect("/app/instance/.backup_tmp.db")
with dst:
    src.backup(dst)          # SQLite online-backup API: consistent even under writes
dst.close(); src.close()
print("snapshot written")
PY

echo "[backup] copying snapshot out of the container"
docker compose cp web:/app/instance/.backup_tmp.db "$OUT"
docker compose exec -T web rm -f /app/instance/.backup_tmp.db

echo "[backup] writing SHA-256 checksum"
sha256sum "$OUT" > "$OUT.sha256"

echo "[backup] pruning backups older than $RETENTION_DAYS days"
find "$BACKUP_DIR" -name 'chateau-*.db*' -mtime +"$RETENTION_DAYS" -delete

echo "[backup] done: $OUT"
ls -lh "$OUT" "$OUT.sha256"
