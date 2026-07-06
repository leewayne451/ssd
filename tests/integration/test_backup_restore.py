"""M12 — backup & recovery (NFR-03 / FSR-25 / FSR-26 / SDR-10).

Snapshots use SQLite's online backup API through the live connection and are
stored under instance/backups/ (outside the web root, SDR-13). The core
NFR-03 metric is the round-trip test: records deleted after a backup come
back after restore. All routes are admin+2FA gated; restore filenames are
validated against the server-generated pattern (no traversal).
"""

import shutil
import time
from pathlib import Path

import pytest

from app.extensions import db
from app.models.audit_log import AuditLog
from app.models.backup_record import BackupRecord
from app.models.enums import UserRole
from app.models.user import User
from app.security import admin_2fa
from app.services import backup_service


@pytest.fixture()
def clean_backups_dir(app):
    """Isolate each test's snapshot files and remove them afterwards."""
    backups = Path(app.instance_path) / "backups"
    if backups.exists():
        shutil.rmtree(backups)
    yield backups
    if backups.exists():
        shutil.rmtree(backups)


def _make_admin_verified(client):
    secret = admin_2fa.generate_secret()
    admin = User(
        email=f"admin{time.time_ns()}@example.com", password_hash="x",
        role=UserRole.ADMIN, status="active",
        totp_secret=secret, totp_enabled=True,
    )
    db.session.add(admin)
    db.session.commit()
    with client.session_transaction() as sess:
        sess["user_id"] = admin.id
        sess["role"] = "admin"
        sess[admin_2fa.SESSION_2FA_FLAG] = True
    return admin


# ------------------- FSR-25: backup ------------------------------------------

def test_admin_creates_backup_with_file_record_and_audit(client, db_session, clean_backups_dir):
    admin = _make_admin_verified(client)

    resp = client.post("/admin/backups/create")
    assert resp.status_code == 302

    record = BackupRecord.query.one()
    assert record.created_by_admin_id == admin.id
    assert record.backup_type == "manual"
    assert record.file_size and record.file_size > 0

    snapshot = clean_backups_dir / record.filename
    assert snapshot.is_file() and snapshot.stat().st_size == record.file_size

    assert AuditLog.query.filter_by(
        action_type="backup_created", target_id=record.id
    ).first() is not None


# ------------------- NFR-03 / FSR-26 / SDR-10: restore round-trip ------------

def test_restore_round_trip_recovers_deleted_records(client, db_session, clean_backups_dir):
    admin = _make_admin_verified(client)

    precious = User(email="precious@example.com", password_hash="x",
                    role=UserRole.BUYER, status="active")
    db.session.add(precious)
    db.session.commit()

    record = backup_service.create_backup(admin)

    # Simulate data loss after the snapshot.
    db.session.delete(precious)
    db.session.commit()
    assert User.query.filter_by(email="precious@example.com").count() == 0

    restored = backup_service.restore_backup(admin, record.filename)
    assert restored is not None and restored.filename == record.filename

    # The critical record is back (NFR-03 measurement), and the restore
    # itself is audited AFTER the swap so the trail survives.
    assert User.query.filter_by(email="precious@example.com").count() == 1
    assert AuditLog.query.filter_by(action_type="backup_restored").count() == 1


def test_restore_via_route(client, db_session, clean_backups_dir):
    admin = _make_admin_verified(client)
    marker = User(email="marker@example.com", password_hash="x",
                  role=UserRole.BUYER, status="active")
    db.session.add(marker)
    db.session.commit()

    record = backup_service.create_backup(admin)
    db.session.delete(marker)
    db.session.commit()

    resp = client.post("/admin/backups/restore", data={"filename": record.filename})
    assert resp.status_code == 302
    assert User.query.filter_by(email="marker@example.com").count() == 1


# ------------------- hostile input & authorization ---------------------------

def test_restore_rejects_traversal_and_unknown_names(client, db_session, clean_backups_dir):
    admin = _make_admin_verified(client)
    backup_service.create_backup(admin)

    for hostile in (
        "../../instance/chateau.db",
        "..\\..\\app\\config.py",
        "chateau-99999999T999999Z-deadbeef.db",  # well-formed but nonexistent
        "evil.db",
        "",
    ):
        with pytest.raises(ValueError):
            backup_service.restore_backup(admin, hostile)


def test_non_admin_blocked_from_backup_surface(client, db_session, login_as):
    login_as("plain@example.com")
    assert client.get("/admin/backups").status_code == 403
    assert client.post("/admin/backups/create").status_code == 403
    assert client.post("/admin/backups/restore", data={"filename": "x"}).status_code == 403


def test_anonymous_blocked_from_backup_surface(client, db_session):
    assert client.get("/admin/backups").status_code == 401
    assert client.post("/admin/backups/create").status_code == 401
