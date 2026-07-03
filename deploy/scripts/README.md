# Operational scripts — Château Collective VM

## backup.sh — daily database backup

Creates a consistent snapshot of the SQLite database using SQLite's online
`.backup` API (safe under concurrent writes), stores it timestamped in
`~/backups/chateau/` with a SHA-256 checksum, and prunes copies older than
14 days. See the script header for the cron installation line.

**D1 traceability:** FSR-25 (backup functionality), NFSR-11 (recovery
availability), SDR-10 (backup and restore testing), NFSR-17-adjacent
(checksums make tampering with stored backups detectable).

## Restore procedure (documented + tested once for SDR-10 evidence)

```bash
# 1. Pick a backup and VERIFY ITS INTEGRITY first
cd ~/backups/chateau
sha256sum -c chateau-<STAMP>.db.sha256      # must print: OK

# 2. Stop the app (nginx can stay up; it will 502 briefly)
cd ~/ssd
docker compose stop web

# 3. Replace the live DB inside the app-instance volume
docker compose cp ~/backups/chateau/chateau-<STAMP>.db web:/app/instance/chateau.db

# 4. Restart and verify
docker compose start web
curl -fsS http://127.0.0.1/healthz          # -> {"status":"ok"}
```

**Restore test evidence to capture (once):** terminal transcript of a full
backup → checksum-verify → restore → healthz cycle, plus timing (NFSR-11
requires restore within one hour — this procedure takes under two minutes).
