"""M2 — unit tests for the RBAC decorators."""

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


def test_login_required_blocks_anonymous(app):
    @login_required
    def view():
        return 200

    with app.test_request_context():
        assert _status(view) == 401


def test_login_required_allows_authenticated(app):
    @login_required
    def view():
        return 200

    with app.test_request_context():
        session["user_id"] = 1
        assert _status(view) == 200


def test_role_required_anonymous_is_401(app):
    @role_required("seller")
    def view():
        return 200

    with app.test_request_context():
        assert _status(view) == 401


def test_role_required_wrong_role_is_403(app):
    @role_required("seller")
    def view():
        return 200

    with app.test_request_context():
        session["user_id"] = 1
        session["role"] = "buyer"
        assert _status(view) == 403


def test_role_required_correct_role_passes(app):
    @role_required("seller")
    def view():
        return 200

    with app.test_request_context():
        session["user_id"] = 1
        session["role"] = "seller"
        assert _status(view) == 200


def test_role_required_accepts_enum_argument_and_enum_session(app):
    @role_required(UserRole.ADMIN)
    def view():
        return 200

    with app.test_request_context():
        session["user_id"] = 1
        session["role"] = UserRole.ADMIN  # enum in session (pre-serialisation)
        assert _status(view) == 200
