"""Bootstrap credential + forced first-login rotation (FR-02/FSR-02/SDR-11).

`flask seed-admin` with only ADMIN_EMAIL generates a strong single-use
password (printed once to stdout / container logs) and flags the account
must_change_password. Until the account rotates via /auth/change-password,
every authenticated request is quarantined to that page — so admin TOTP
enrolment is only reachable AFTER the bootstrap credential is retired, and
the logged value is dead the moment rotation happens.
"""

import re

from app.extensions import db
from app.models.audit_log import AuditLog
from app.models.enums import UserRole
from app.models.profile import Profile
from app.models.user import User

STRONG_NEW = "Rotated-Correctly-After-Boot-77!"


def _seed_generated(app, email="bootadmin@example.com"):
    """Run seed-admin in generate mode and return (user, temp_password)."""
    runner = app.test_cli_runner()
    result = runner.invoke(args=["seed-admin", "--email", email])
    assert result.exit_code == 0, result.output
    match = re.search(r"SINGLE-USE bootstrap password: (\S+)", result.output)
    assert match, result.output
    return User.query.filter_by(email=email).one(), match.group(1)


def _login(client, email, password):
    return client.post("/auth/login",
                       data={"email": email, "password": password},
                       follow_redirects=True)


# ------------------- seed generate mode --------------------------------------

def test_seed_without_password_generates_single_use_credential(app, db_session):
    admin, temp = _seed_generated(app)

    assert admin.role == UserRole.ADMIN
    assert admin.must_change_password is True
    assert len(temp) >= 20                      # 144-bit token_urlsafe
    assert admin.password_hash != temp          # stored hashed
    assert Profile.query.filter_by(user_id=admin.id).count() == 1

    row = AuditLog.query.filter_by(action_type="admin_seeded", target_id=admin.id).one()
    assert "bootstrap_password" in (row.details or "")


def test_seed_with_explicit_password_is_not_force_rotated(app, db_session):
    runner = app.test_cli_runner()
    result = runner.invoke(args=["seed-admin", "--email", "devadmin@example.com",
                                 "--password", "Correct-Horse-Battery-Staple-31!"])
    assert result.exit_code == 0, result.output
    assert "SINGLE-USE" not in result.output

    admin = User.query.filter_by(email="devadmin@example.com").one()
    assert admin.must_change_password is False


def test_seed_password_without_email_still_fails(app, db_session):
    runner = app.test_cli_runner()
    result = runner.invoke(args=["seed-admin", "--password", "Whatever-Strong-1!"])
    assert result.exit_code != 0
    assert User.query.count() == 0


# ------------------- quarantine ----------------------------------------------

def test_flagged_account_is_quarantined_to_change_password(app, client, db_session):
    admin, temp = _seed_generated(app)
    resp = _login(client, admin.email, temp)
    assert resp.status_code == 200

    # Any page redirects to the rotation form...
    for path in ("/", "/listings", "/admin/", f"/profile/{admin.id}"):
        r = client.get(path)
        assert r.status_code == 302, path
        assert "/auth/change-password" in r.headers["Location"], path

    # ...while the form itself and logout stay reachable.
    assert client.get("/auth/change-password").status_code == 200
    assert client.get("/auth/logout").status_code == 302


def test_quarantine_does_not_touch_normal_users(client, db_session, login_as):
    login_as("normaluser@example.com")
    assert client.get("/listings").status_code == 200


# ------------------- rotation ------------------------------------------------

def test_rotation_clears_flag_kills_temp_password_and_audits(app, client, db_session):
    admin, temp = _seed_generated(app)
    _login(client, admin.email, temp)

    resp = client.post("/auth/change-password", data={
        "current_password": temp,
        "new_password": STRONG_NEW,
        "confirm_password": STRONG_NEW,
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Password changed successfully" in resp.data

    db.session.refresh(admin)
    assert admin.must_change_password is False
    assert AuditLog.query.filter_by(
        action_type="password_changed", target_id=admin.id
    ).count() == 1

    # Quarantine lifted.
    assert client.get("/listings").status_code == 200

    # The bootstrap credential is dead: a fresh login with it fails...
    fresh = client.application.test_client()
    denied = _login(fresh, admin.email, temp)
    assert b"Invalid email or password." in denied.data
    # ...and the new password works.
    ok = _login(fresh, admin.email, STRONG_NEW)
    assert b"Logged in successfully" in ok.data


def test_rotation_requires_correct_current_password(app, client, db_session):
    admin, temp = _seed_generated(app)
    _login(client, admin.email, temp)

    resp = client.post("/auth/change-password", data={
        "current_password": "not-the-temp-password",
        "new_password": STRONG_NEW,
        "confirm_password": STRONG_NEW,
    }, follow_redirects=True)
    assert b"Current password is incorrect" in resp.data

    db.session.refresh(admin)
    assert admin.must_change_password is True   # still quarantined
    assert AuditLog.query.filter_by(action_type="password_change_failed").count() == 1


def test_rotation_enforces_password_policy(app, client, db_session):
    admin, temp = _seed_generated(app)
    _login(client, admin.email, temp)

    resp = client.post("/auth/change-password", data={
        "current_password": temp,
        "new_password": "password123",
        "confirm_password": "password123",
    }, follow_redirects=True)
    assert resp.status_code == 200

    db.session.refresh(admin)
    assert admin.must_change_password is True   # weak password rejected


def test_change_password_available_to_normal_users(client, db_session, login_as):
    user = login_as("rotator@example.com", password="MySecureP@ssw0rd!2026")

    resp = client.post("/auth/change-password", data={
        "current_password": "MySecureP@ssw0rd!2026",
        "new_password": STRONG_NEW,
        "confirm_password": STRONG_NEW,
    }, follow_redirects=True)
    assert b"Password changed successfully" in resp.data

    fresh = client.application.test_client()
    assert b"Logged in successfully" in _login(fresh, user.email, STRONG_NEW).data


def test_anonymous_cannot_reach_change_password(client, db_session):
    assert client.get("/auth/change-password").status_code == 401
