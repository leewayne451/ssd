"""Admin lockout visibility + unlock (FSR-05 — UI-audit item 6).

Brute-force lockouts previously expired only by clock and were invisible to
admins. The users page now flags locked accounts and offers an audited
unlock; a released user can log in immediately.
"""

import time
from datetime import datetime, timedelta, timezone

from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models.audit_log import AuditLog
from app.models.enums import UserRole
from app.models.user import User
from app.security import admin_2fa


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


def _locked_user(email="lockedout@example.com", password="MySecureP@ssw0rd!2026"):
    user = User(
        email=email,
        password_hash=generate_password_hash(password),
        role=UserRole.BUYER,
        status="active",
        failed_login_attempts=5,
        locked_until=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    db.session.add(user)
    db.session.commit()
    return user


def test_users_page_flags_locked_accounts(client, db_session):
    _make_admin_verified(client)
    _locked_user()

    resp = client.get("/admin/users")
    assert resp.status_code == 200
    assert b">locked<" in resp.data
    assert b"5 failed logins" in resp.data
    assert b"Unlock" in resp.data


def test_admin_unlock_clears_lockout_and_audits(client, db_session):
    admin = _make_admin_verified(client)
    user = _locked_user()

    resp = client.post(f"/admin/users/{user.id}/unlock")
    assert resp.status_code == 302

    db.session.refresh(user)
    assert user.locked_until is None
    assert user.failed_login_attempts == 0

    row = AuditLog.query.filter_by(action_type="user_unlocked", target_id=user.id).first()
    assert row is not None and row.actor_user_id == admin.id


def test_unlocked_user_can_log_in_immediately(client, db_session):
    admin = _make_admin_verified(client)
    password = "MySecureP@ssw0rd!2026"
    user = _locked_user(password=password)

    # Locked: real login path refuses even the right password.
    fresh = client.application.test_client()
    denied = fresh.post("/auth/login",
                        data={"email": user.email, "password": password},
                        follow_redirects=True)
    assert b"locked" in denied.data.lower()

    client.post(f"/admin/users/{user.id}/unlock")

    allowed = fresh.post("/auth/login",
                         data={"email": user.email, "password": password},
                         follow_redirects=True)
    assert allowed.status_code == 200
    assert b"Logged in successfully" in allowed.data


def test_non_admin_cannot_unlock(client, db_session, login_as):
    user = _locked_user()
    login_as("nounlock@example.com")
    assert client.post(f"/admin/users/{user.id}/unlock").status_code == 403
    db.session.refresh(user)
    assert user.locked_until is not None
