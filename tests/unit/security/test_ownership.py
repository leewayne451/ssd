"""M2 — unit tests for ownership / IDOR enforcement."""

import pytest
from werkzeug.exceptions import HTTPException

from app.security.ownership import assert_owner


class _Listing:
    def __init__(self, seller_id):
        self.seller_id = seller_id


class _User:
    def __init__(self, uid):
        self.id = uid


def _code(callable_):
    try:
        callable_()
    except HTTPException as exc:
        return exc.code
    return 200


def test_owner_object_matches(app):
    with app.test_request_context():
        assert assert_owner(_Listing(7), _User(7), owner_attr="seller_id") is True


def test_owner_object_mismatch_is_403(app):
    with app.test_request_context():
        assert _code(lambda: assert_owner(_Listing(7), _User(8), owner_attr="seller_id")) == 403


def test_owner_accepts_bare_user_id(app):
    with app.test_request_context():
        assert assert_owner(_Listing(7), 7, owner_attr="seller_id") is True


def test_owner_dict_resource(app):
    with app.test_request_context():
        assert assert_owner({"seller_id": 5}, 5, owner_attr="seller_id") is True
        assert _code(lambda: assert_owner({"seller_id": 5}, 6, owner_attr="seller_id")) == 403


def test_missing_resource_is_404(app):
    with app.test_request_context():
        assert _code(lambda: assert_owner(None, 1, owner_attr="seller_id")) == 404


def test_anonymous_user_is_401(app):
    with app.test_request_context():
        assert _code(lambda: assert_owner(_Listing(7), None, owner_attr="seller_id")) == 401


def test_fails_closed_when_owner_unknown(app):
    """A resource with no owner id must not be treated as owned by anyone."""
    with app.test_request_context():
        assert _code(lambda: assert_owner({"title": "x"}, 1, owner_attr="seller_id")) == 403


def test_owner_attr_inferred_when_not_given(app):
    with app.test_request_context():
        assert assert_owner({"buyer_id": 9}, 9) is True
        assert _code(lambda: assert_owner({"buyer_id": 9}, 1)) == 403
