"""M1 — registration fields, hashing, session lifecycle, auth audit (T-01..T-08).

Covers FR-01, FSR-03/04/13, SDR-05/06, OWASP mapping rows 4, 13, 14, 17
and the login-time half of FR-13 (suspended accounts).
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.extensions import db
from app.models.audit_log import AuditLog
from app.models.enums import AccountStatus
from app.models.profile import Profile
from app.models.security_event import SecurityEvent
from app.models.user import User
from app.services.auth_service import register_user

STRONG_PASSWORD = "MySecureP@ssw0rd!2026"


# ------------------- FR-01: registration fields (T-01, T-02) ----------------

def test_register_captures_name_phone_and_creates_profile(client, db_session):
    """T-01: FR-01 requires name, email, phone, password — and a Profile row."""
    resp = client.post("/auth/register", data={
        "name": "Ada Lovelace",
        "email": "ada@example.com",
        "phone": "+65 9123 4567",
        "password": STRONG_PASSWORD,
        "confirm_password": STRONG_PASSWORD,
    }, follow_redirects=False)
    assert resp.status_code == 302  # redirect to login on success

    user = User.query.filter_by(email="ada@example.com").one()
    profile = Profile.query.filter_by(user_id=user.id).one()
    assert profile.first_name == "Ada"
    assert profile.last_name == "Lovelace"
    assert profile.phone_number == "+65 9123 4567"


@pytest.mark.parametrize("bad_field, bad_value", [
    ("phone", "not-a-phone"),
    ("phone", "12"),                # too short
    ("name", "A"),                  # too short
    ("name", "x" * 101),            # too long
])
def test_register_rejects_invalid_name_or_phone(client, db_session, bad_field, bad_value):
    """T-02: invalid name/phone re-renders the form and creates no account."""
    data = {
        "name": "Valid Name",
        "email": "reject-me@example.com",
        "phone": "+65 9123 4567",
        "password": STRONG_PASSWORD,
        "confirm_password": STRONG_PASSWORD,
    }
    data[bad_field] = bad_value

    resp = client.post("/auth/register", data=data)
    assert resp.status_code == 200  # form re-rendered with errors
    assert User.query.filter_by(email="reject-me@example.com").first() is None


# ------------------- FSR-03 / SDR-05: hashed storage (T-03) -----------------

def test_password_stored_as_hash_not_plaintext(client, db_session):
    """T-03: the DB value is a salted hash, never the plaintext."""
    user, err = register_user("hash-check@example.com", STRONG_PASSWORD)
    assert err is None

    stored = User.query.filter_by(email="hash-check@example.com").one().password_hash
    assert stored != STRONG_PASSWORD
    assert STRONG_PASSWORD not in stored
    # Werkzeug hashes carry a method$salt$hash structure
    assert stored.count("$") >= 2


# ------------------- FSR-04: inactivity timeout (T-04) ----------------------

def test_session_expires_after_inactivity(client, login_as, app):
    """T-04: a session idle past SESSION_TIMEOUT_MINUTES is terminated."""
    login_as("timeout@example.com")
    assert client.get("/cart").status_code == 200  # alive while active

    timeout = app.config.get("SESSION_TIMEOUT_MINUTES", 30)
    stale = datetime.now(timezone.utc) - timedelta(minutes=timeout + 1)
    with client.session_transaction() as sess:
        sess["last_activity"] = stale.isoformat()

    resp = client.get("/cart", follow_redirects=False)
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_activity_within_limit_keeps_session_alive(client, login_as):
    """T-04b: recent activity refreshes the window instead of expiring it."""
    login_as("stay-alive@example.com")

    recent = datetime.now(timezone.utc) - timedelta(minutes=5)
    with client.session_transaction() as sess:
        sess["last_activity"] = recent.isoformat()

    assert client.get("/cart").status_code == 200
    with client.session_transaction() as sess:
        # the timestamp was refreshed by the request
        refreshed = datetime.fromisoformat(sess["last_activity"])
        assert refreshed.replace(tzinfo=timezone.utc) > recent


# ------------------- session fixation (T-05) --------------------------------

def test_login_discards_pre_login_session_content(client, db_session):
    """T-05: login regenerates the session — attacker-planted keys don't survive."""
    register_user("fixation@example.com", STRONG_PASSWORD)

    with client.session_transaction() as sess:
        sess["canary"] = "planted-before-login"

    client.post("/auth/login", data={
        "email": "fixation@example.com",
        "password": STRONG_PASSWORD,
    })

    with client.session_transaction() as sess:
        assert sess.get("user_id") is not None
        assert "canary" not in sess


# ------------------- FSR-13 / FSR-11: auth audit trail (T-06) ---------------

def test_auth_events_write_audit_rows(client, db_session):
    """T-06: register / failed login / successful login / logout all leave rows."""
    client.post("/auth/register", data={
        "name": "Audit Trail",
        "email": "audit@example.com",
        "phone": "91234567",
        "password": STRONG_PASSWORD,
        "confirm_password": STRONG_PASSWORD,
    })
    client.post("/auth/login", data={
        "email": "audit@example.com", "password": "WrongPassword1!",
    })
    client.post("/auth/login", data={
        "email": "audit@example.com", "password": STRONG_PASSWORD,
    })
    client.get("/auth/logout")

    actions = {row.action_type for row in AuditLog.query.all()}
    assert "user_registered" in actions
    assert "login_failed" in actions
    assert "login_success" in actions
    assert "logout" in actions

    # NFSR-18 / row 23: no secrets in any audit row
    for row in AuditLog.query.all():
        assert STRONG_PASSWORD not in (row.details or "")


# ------------------- FR-13: suspended accounts (T-07) -----------------------

def test_suspended_user_cannot_login(client, db_session):
    """T-07: suspension denies login with the generic error + security event."""
    user, _ = register_user("suspended@example.com", STRONG_PASSWORD)
    user.status = AccountStatus.SUSPENDED
    db.session.commit()

    resp = client.post("/auth/login", data={
        "email": "suspended@example.com", "password": STRONG_PASSWORD,
    }, follow_redirects=True)

    assert b"Invalid email or password." in resp.data  # generic, no state leak
    with client.session_transaction() as sess:
        assert "user_id" not in sess

    event = SecurityEvent.query.filter_by(event_type="suspended_login_denied").first()
    assert event is not None
    assert event.user_id == user.id


# ------------------- SDR-06: no session reuse after logout (T-08) -----------

def test_session_not_reusable_after_logout(client, login_as):
    """T-08: after logout the same client (same cookie jar) is anonymous."""
    login_as("reuse@example.com")
    assert client.get("/cart").status_code == 200

    client.get("/auth/logout")

    assert client.get("/cart").status_code == 401
