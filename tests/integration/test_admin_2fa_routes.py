"""M2 — route-level tests for admin RBAC + the admin 2FA gate."""

import time

import pytest

from app.extensions import db
from app.models.user import User
from app.models.enums import UserRole
from app.security import admin_2fa


def _make_admin(enabled=False, secret=None):
    user = User(
        email=f"admin{time.time_ns()}@example.com",
        password_hash="x",
        role=UserRole.ADMIN,
        status="active",
        totp_secret=secret,
        totp_enabled=enabled,
    )
    db.session.add(user)
    db.session.commit()
    return user


def _login(client, user_id, role):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["role"] = role


# --- RBAC on the admin landing page --------------------------------------

def test_admin_index_anonymous_is_401(client):
    assert client.get("/admin/").status_code == 401


def test_admin_index_buyer_is_403(client):
    _login(client, 999, "buyer")
    assert client.get("/admin/").status_code == 403


# --- admin 2FA gate -------------------------------------------------------

def test_admin_not_enrolled_redirected_to_setup(client, db_session):
    admin = _make_admin(enabled=False)
    _login(client, admin.id, "admin")

    resp = client.get("/admin/")
    assert resp.status_code == 302
    assert "/admin/2fa/setup" in resp.headers["Location"]


def test_admin_enrolled_unverified_redirected_to_verify(client, db_session):
    secret = admin_2fa.generate_secret()
    admin = _make_admin(enabled=True, secret=secret)
    _login(client, admin.id, "admin")

    resp = client.get("/admin/")
    assert resp.status_code == 302
    assert "/admin/2fa/verify" in resp.headers["Location"]


def test_admin_index_accessible_once_verified(client, db_session):
    secret = admin_2fa.generate_secret()
    admin = _make_admin(enabled=True, secret=secret)
    _login(client, admin.id, "admin")
    with client.session_transaction() as sess:
        sess[admin_2fa.SESSION_2FA_FLAG] = True

    resp = client.get("/admin/")
    assert resp.status_code == 200


# --- verify route ---------------------------------------------------------

def test_verify_with_valid_code_unlocks_admin(client, db_session):
    secret = admin_2fa.generate_secret()
    admin = _make_admin(enabled=True, secret=secret)
    _login(client, admin.id, "admin")

    code = admin_2fa.totp_at(secret, time.time())
    resp = client.post("/admin/2fa/verify", data={"code": code})
    assert resp.status_code == 302

    # Session is now marked verified; the admin page is reachable.
    assert client.get("/admin/").status_code == 200


def test_verify_with_invalid_code_stays_locked(client, db_session):
    secret = admin_2fa.generate_secret()
    admin = _make_admin(enabled=True, secret=secret)
    _login(client, admin.id, "admin")

    resp = client.post("/admin/2fa/verify", data={"code": "000000"})
    assert resp.status_code == 200  # re-rendered form, not a redirect

    # Still gated.
    follow = client.get("/admin/")
    assert follow.status_code == 302
    assert "/admin/2fa/verify" in follow.headers["Location"]


def test_2fa_routes_require_admin(client):
    # Anonymous -> 401, buyer -> 403, on both setup and verify.
    assert client.get("/admin/2fa/verify").status_code == 401
    assert client.get("/admin/2fa/setup").status_code == 401
    _login(client, 123, "buyer")
    assert client.get("/admin/2fa/verify").status_code == 403
    assert client.get("/admin/2fa/setup").status_code == 403


# --- setup / enrolment flow ----------------------------------------------

def test_setup_enrols_admin_with_valid_code(client, db_session):
    admin = _make_admin(enabled=False)
    _login(client, admin.id, "admin")

    # First GET generates and stashes a pending secret.
    assert client.get("/admin/2fa/setup").status_code == 200
    with client.session_transaction() as sess:
        secret = sess["pending_totp_secret"]

    code = admin_2fa.totp_at(secret, time.time())
    resp = client.post("/admin/2fa/setup", data={"code": code})
    assert resp.status_code == 302

    refreshed = db.session.get(User, admin.id)
    assert refreshed.totp_enabled is True
    assert refreshed.totp_secret == secret
    # Enrolment also satisfies this session's 2FA challenge.
    assert client.get("/admin/").status_code == 200
