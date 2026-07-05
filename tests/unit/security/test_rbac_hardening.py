"""M2 hardening — stale sessions, live suspension, live role changes (T-09..T-11, T-13).

These lock in the fail-closed behaviour that replaced Flask-Login's
"failed user load = anonymous" semantics:

  * a session whose user no longer exists is treated as anonymous (401),
    never a 500 inside the view;
  * suspending a user kills their already-active session on the very next
    request (CONFLICT-002 — not just at next login);
  * an admin role change takes effect without re-login.
"""

import pytest
from werkzeug.exceptions import HTTPException
from flask import session

from app.models.enums import UserRole, AccountStatus
from app.models.security_event import SecurityEvent
from app.security.rbac import login_required, role_required


def _status(fn):
    try:
        result = fn()
    except HTTPException as exc:
        return exc.code
    return result


def test_stale_session_for_deleted_user_is_401_not_500(app, db_session):
    """T-09: a live session referencing a missing user fails closed as anonymous."""

    @login_required
    def view():
        return 200

    with app.test_request_context():
        session["user_id"] = 999_999  # no such row
        assert _status(view) == 401
        # fail-closed also scrubs the poisoned session
        assert "user_id" not in session

    event = SecurityEvent.query.filter_by(event_type="stale_session_rejected").first()
    assert event is not None


def test_suspension_kills_active_session_on_next_request(app, make_user):
    """T-10: suspension takes effect on the next request, not the next login."""
    user = make_user("suspend-live@test.local", role=UserRole.BUYER)

    @login_required
    def view():
        return 200

    # Session established while active…
    with app.test_request_context():
        session["user_id"] = user.id
        assert _status(view) == 200

    # …admin suspends the account…
    user.status = AccountStatus.SUSPENDED

    # …and the very next request is rejected and the session cleared.
    with app.test_request_context():
        session["user_id"] = user.id
        assert _status(view) == 401
        assert "user_id" not in session

    event = SecurityEvent.query.filter_by(event_type="suspended_session_rejected").first()
    assert event is not None
    assert event.user_id == user.id


def test_role_change_takes_effect_without_relogin(app, make_user):
    """T-11: role_required authorises against the DB role on every request."""
    user = make_user("role-change@test.local", role=UserRole.SELLER)

    @role_required("seller")
    def seller_view():
        return 200

    with app.test_request_context():
        session["user_id"] = user.id
        assert _status(seller_view) == 200

    # Admin demotes the account; no re-login happens.
    user.role = UserRole.BUYER

    with app.test_request_context():
        session["user_id"] = user.id
        assert _status(seller_view) == 403


def test_dev_login_route_disabled_outside_debug_and_testing(app, client, db_session):
    """T-13: the dev quick-login helper must be dead in production-like config."""
    old_testing = app.config.get("TESTING", False)
    old_debug = app.debug
    app.config["TESTING"] = False
    app.debug = False
    try:
        resp = client.get("/dev/login_as_seller")
        assert resp.status_code == 403
    finally:
        app.config["TESTING"] = old_testing
        app.debug = old_debug
