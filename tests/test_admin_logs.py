from app.models.audit_log import AuditLog
from app.models.enums import UserRole
from app.security.admin_2fa import generate_secret


# ---------------------------------------------------------------------------
# #30 — Admin log viewer access control
# ---------------------------------------------------------------------------

def test_non_admin_blocked_from_logs(client, buyer, db_session):
    # NEGATIVE: buyer role should get 403 on /admin/logs
    with client.session_transaction() as sess:
        sess["user_id"] = buyer.id
        sess["role"] = buyer.role.value
    resp = client.get("/admin/logs")
    assert resp.status_code == 403


def test_unauthenticated_blocked_from_logs(client, db_session):
    # NEGATIVE: no session at all should get 401
    resp = client.get("/admin/logs")
    assert resp.status_code == 401


def test_admin_without_2fa_redirected(client, admin_user, db_session):
    # NEGATIVE: admin with no TOTP enrolled should be redirected to setup, not 200
    with client.session_transaction() as sess:
        sess["user_id"] = admin_user.id
        sess["role"] = admin_user.role.value
        # no admin_2fa_verified in session
    resp = client.get("/admin/logs")
    assert resp.status_code == 302  # redirect to 2FA setup


def test_admin_with_2fa_can_access_logs(client, admin_user, db_session):
    # POSITIVE: admin with TOTP enrolled + session verified should reach log viewer
    admin_user.totp_secret = generate_secret()
    admin_user.totp_enabled = True
    db_session.flush()

    with client.session_transaction() as sess:
        sess["user_id"] = admin_user.id
        sess["role"] = admin_user.role.value
        sess["admin_2fa_verified"] = True
    resp = client.get("/admin/logs")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# #31 — Non-admin 403 on /admin root
# ---------------------------------------------------------------------------

def test_non_admin_blocked_from_admin_root(client, buyer, db_session):
    # NEGATIVE: buyer cannot access /admin at all
    with client.session_transaction() as sess:
        sess["user_id"] = buyer.id
        sess["role"] = buyer.role.value
    resp = client.get("/admin/")
    assert resp.status_code == 403


def test_audit_log_viewer_is_read_only(client, admin_user, db_session):
    # NEGATIVE: POST to /admin/logs should be method not allowed
    admin_user.totp_secret = generate_secret()
    admin_user.totp_enabled = True
    db_session.flush()

    with client.session_transaction() as sess:
        sess["user_id"] = admin_user.id
        sess["role"] = admin_user.role.value
        sess["admin_2fa_verified"] = True
    resp = client.post("/admin/logs")
    assert resp.status_code == 405