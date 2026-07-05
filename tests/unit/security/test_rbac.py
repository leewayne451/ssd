"""M2 — unit tests for the RBAC decorators.

The decorators authorise against the DATABASE user (role, status), not
session-stored values, so every test builds a real User row first.
"""

import pytest
from werkzeug.exceptions import HTTPException
from flask import session

from app.models.enums import UserRole
from app.security.rbac import login_required, role_required, _role_value


def _status(fn):
    """Call a wrapped view, returning its HTTP status code (raised or returned)."""
    try:
        result = fn()
    except HTTPException as exc:
        return exc.code
    return result


def test_role_value_normalises_enum_and_str():
    assert _role_value(UserRole.SELLER) == "seller"
    assert _role_value("seller") == "seller"
    assert _role_value(None) is None


def test_login_required_blocks_anonymous(app, db_session):
    @login_required
    def view():
        return 200

    with app.test_request_context():
        assert _status(view) == 401


def test_login_required_allows_authenticated(app, make_user):
    user = make_user("rbac-auth@test.local")

    @login_required
    def view():
        return 200

    with app.test_request_context():
        session["user_id"] = user.id
        assert _status(view) == 200


def test_role_required_anonymous_is_401(app, db_session):
    @role_required("seller")
    def view():
        return 200

    with app.test_request_context():
        assert _status(view) == 401


def test_role_required_wrong_role_is_403(app, make_user):
    buyer = make_user("rbac-buyer@test.local", role=UserRole.BUYER)

    @role_required("seller")
    def view():
        return 200

    with app.test_request_context():
        session["user_id"] = buyer.id
        assert _status(view) == 403


def test_role_required_correct_role_passes(app, make_user):
    seller = make_user("rbac-seller@test.local", role=UserRole.SELLER)

    @role_required("seller")
    def view():
        return 200

    with app.test_request_context():
        session["user_id"] = seller.id
        assert _status(view) == 200


def test_role_required_accepts_enum_argument(app, make_user):
    admin = make_user("rbac-admin@test.local", role=UserRole.ADMIN)

    @role_required(UserRole.ADMIN)
    def view():
        return 200

    with app.test_request_context():
        session["user_id"] = admin.id
        assert _status(view) == 200


def test_role_from_db_wins_over_session_value(app, make_user):
    """A tampered/stale session role is ignored — the DB role is authoritative."""
    buyer = make_user("rbac-tamper@test.local", role=UserRole.BUYER)

    @role_required("seller")
    def view():
        return 200

    with app.test_request_context():
        session["user_id"] = buyer.id
        session["role"] = "seller"  # forged/stale client-side value
        assert _status(view) == 403
