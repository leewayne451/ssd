# backup_service — application-level backup & recovery (M12).
#
# D1: NFR-03 ("a database backup shall be restorable in the test environment
# without loss of critical records"), FSR-25/26 (backup + recovery
# functionality), SDR-10 (backup/restore testing), SDR-13 (backups live under
# instance/, outside the web root — never URL-addressable).
#
# Snapshots use SQLite's online backup API through the live SQLAlchemy
# connection, so they are consistent even mid-write — the DB file is never
# copied raw. The host-level daily cron (deploy/scripts/backup.sh) is the
# second, deploy-layer line of the same control.
import logging
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from flask import current_app

from app.extensions import db
from app.models.backup_record import BackupRecord
from app.services.audit_service import record as audit_record

logger = logging.getLogger(__name__)

# Server-generated names only: timestamp + random suffix. Anything else —
# traversal attempts included — is rejected before touching the filesystem.
_BACKUP_NAME_RE = re.compile(r"^chateau-\d{8}T\d{6}Z-[0-9a-f]{8}\.db$")


def _backups_dir() -> Path:
    path = Path(current_app.instance_path) / "backups"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _live_sqlite_connection() -> sqlite3.Connection:
    """The DBAPI connection SQLAlchemy is using (works for file and memory DBs)."""
    raw = db.engine.raw_connection()
    return getattr(raw, "driver_connection", None) or raw.connection


def create_backup(admin) -> BackupRecord:
    """
    Snapshot the database into instance/backups/ and record it.

    The BackupRecord row is committed BEFORE the snapshot runs, so the backup
    file contains its own record — after a later restore, the file remains
    listed and restorable again.
    """
    filename = "chateau-{stamp}-{suffix}.db".format(
        stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        suffix=uuid.uuid4().hex[:8],
    )
    target = _backups_dir() / filename

    record = BackupRecord(
        filename=filename,
        backup_type="manual",
        created_by_admin_id=admin.id if admin else None,
    )
    db.session.add(record)
    db.session.commit()

    src = _live_sqlite_connection()
    dest = sqlite3.connect(str(target))
    try:
        src.backup(dest)
    finally:
        dest.close()

    record.file_size = target.stat().st_size
    db.session.commit()

    audit_record(admin, "backup_created", "backup", record.id,
                 {"filename": filename})
    return record


def list_backups() -> list[BackupRecord]:
    return (
        BackupRecord.query.order_by(
            BackupRecord.created_at.desc(), BackupRecord.id.desc()
        ).all()
    )


def restore_backup(admin, filename: str) -> BackupRecord:
    """
    Restore the database from a previously created backup (FSR-26).

    Defence in depth before any filesystem access:
      * the name must match the server-generated pattern (no traversal,
        no user-controlled paths — SDR-04 discipline applied to backups);
      * the resolved path must stay inside instance/backups/;
      * a BackupRecord row for that name must exist.

    The restore audit row is written AFTER the data is swapped so the
    action survives its own restore. Raises ValueError on any rejection.
    """
    filename = (filename or "").strip()
    if not _BACKUP_NAME_RE.fullmatch(filename):
        raise ValueError("unknown backup")

    backups_dir = _backups_dir().resolve()
    source_path = (backups_dir / filename).resolve()
    if source_path.parent != backups_dir or not source_path.is_file():
        raise ValueError("unknown backup")

    record = BackupRecord.query.filter_by(filename=filename).first()
    if record is None:
        raise ValueError("unknown backup")
    record_id = record.id
    admin_id = admin.id if admin else None

    # Release ORM state: open sessions would hold transactions on the target,
    # and every loaded object (including `admin`) becomes detached.
    db.session.remove()

    source = sqlite3.connect(str(source_path))
    try:
        source.backup(_live_sqlite_connection())
    finally:
        source.close()

    # Re-fetch the actor from the restored data — the pre-restore object is
    # detached and would silently break the audit write.
    from app.models.user import User

    actor = db.session.get(User, admin_id) if admin_id else None
    audit_record(actor, "backup_restored", "backup", record_id,
                 {"filename": filename})
    return db.session.get(BackupRecord, record_id)
