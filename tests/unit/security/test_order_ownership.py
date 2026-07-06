"""M2 — order-workflow ownership helpers (T-12).

Role checks answer "are you a seller?"; these answer "are you THIS order's
seller/buyer?" — the missing half of CTRL-002 (seller fraud / IDOR).
"""

import pytest
from werkzeug.exceptions import HTTPException

from app.models.enums import UserRole
from app.security.ownership import (
    require_order_buyer,
    require_order_seller,
    user_is_order_buyer,
    user_owns_order_listing,
)


def _code(fn, *args):
    try:
        fn(*args)
    except HTTPException as exc:
        return exc.code
    return 200


def test_buyer_helper_matches_order_buyer(order, buyer_user):
    assert user_is_order_buyer(order, buyer_user) is True


def test_buyer_helper_rejects_other_users(order, seller_user, make_user):
    other_buyer = make_user("other-buyer@test.local", role=UserRole.BUYER)
    assert user_is_order_buyer(order, other_buyer) is False
    assert user_is_order_buyer(order, seller_user) is False
    assert user_is_order_buyer(order, None) is False
    assert user_is_order_buyer(None, seller_user) is False


def test_seller_helper_matches_listing_seller(order, seller_user):
    assert user_owns_order_listing(order, seller_user) is True


def test_seller_helper_rejects_other_sellers(order, buyer_user, make_user):
    seller_b = make_user("seller-b@test.local", role=UserRole.SELLER)
    assert user_owns_order_listing(order, seller_b) is False
    assert user_owns_order_listing(order, buyer_user) is False
    assert user_owns_order_listing(order, None) is False


def test_require_order_seller_guards(app, order, seller_user, make_user):
    seller_b = make_user("seller-c@test.local", role=UserRole.SELLER)
    with app.test_request_context():
        assert _code(require_order_seller, order, seller_user) == 200
        assert _code(require_order_seller, order, seller_b) == 403
        assert _code(require_order_seller, order, None) == 401
        assert _code(require_order_seller, None, seller_user) == 404


def test_require_order_buyer_guards(app, order, buyer_user, seller_user):
    with app.test_request_context():
        assert _code(require_order_buyer, order, buyer_user) == 200
        assert _code(require_order_buyer, order, seller_user) == 403
        assert _code(require_order_buyer, order, None) == 401
        assert _code(require_order_buyer, None, buyer_user) == 404
