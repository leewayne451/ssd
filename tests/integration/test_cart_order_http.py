"""HTTP-level cart/order tests (T-22, T-29).

T-22 is the Flask-Login-removal proving test: before the swap, every
cart/order route rejected ALL logged-in users because nothing ever called
flask_login.login_user(). Logging in through the real /auth/login route and
loading /cart was literally impossible; this file keeps it possible.
"""

import pytest

from app.models.enums import UserRole, WorkflowStatus
from app.models.order import Order


def test_cart_requires_login(client, db_session):
    assert client.get("/cart").status_code == 401


def test_login_then_load_cart_page(client, login_as):
    """T-22: real login -> cart page renders for the session user."""
    login_as("cart-buyer@example.com")

    resp = client.get("/cart")
    assert resp.status_code == 200
    assert b"Your cart" in resp.data


def test_add_item_then_cart_shows_it(client, login_as, approved_listing):
    login_as("cart-buyer2@example.com")

    resp = client.post(
        "/cart/add",
        data={"listing_id": approved_listing.id, "quantity": 1},
        follow_redirects=True,
    )
    assert resp.status_code == 200

    page = client.get("/cart")
    assert page.status_code == 200
    assert approved_listing.title.encode() in page.data


def test_place_order_from_cart_over_http(client, login_as, approved_listing):
    buyer = login_as("cart-buyer3@example.com")

    client.post("/cart/add", data={"listing_id": approved_listing.id, "quantity": 1})
    resp = client.post("/orders/place", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Your orders" in resp.data

    order = Order.query.filter_by(buyer_id=buyer.id).first()
    assert order is not None
    assert order.workflow_status == WorkflowStatus.COMMITTED


def test_buyer_cannot_view_other_buyers_order_over_http(client, login_as, order):
    """T-29: order detail is buyer-private (FSR-08 / NFSR-02)."""
    login_as("intruder@example.com")  # a different buyer than the order's

    resp = client.get(f"/orders/{order.id}")
    assert resp.status_code == 403


def test_buyer_can_view_own_order_over_http(client, login_as, approved_listing, db_session):
    buyer = login_as("own-order@example.com")
    my_order = Order(
        buyer_id=buyer.id,
        listing_id=approved_listing.id,
        committed_price=approved_listing.price,
        workflow_status=WorkflowStatus.COMMITTED,
    )
    db_session.add(my_order)
    db_session.commit()

    resp = client.get(f"/orders/{my_order.id}")
    assert resp.status_code == 200
    assert f"Order #{my_order.id}".encode() in resp.data
