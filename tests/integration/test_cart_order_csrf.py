import hashlib
import os

from flask import session
from flask_wtf.csrf import generate_csrf


def create_csrf_token(app, client):
    resp = client.get("/_test/csrf-token")
    assert resp.status_code == 200
    with client.session_transaction() as sess:
        print('DEBUG session after token', dict(sess))
    return resp.get_data(as_text=True)


def test_cart_add_requires_csrf_token(app, client, db_session, make_user):
    app.config["WTF_CSRF_ENABLED"] = True
    buyer = make_user("csrfbuyer@test.local")

    from app.models.product_listing import ProductListing

    listing = ProductListing(
        seller_id=999,
        title="CSRF Item",
        description="desc",
        category="misc",
        brand="Acme",
        price=10.00,
        condition="new",
        approval_status="approved",
        workflow_status="available",
        is_active=True,
    )
    db_session.add(listing)
    db_session.flush()

    with client.session_transaction() as sess:
        sess["user_id"] = buyer.id
        sess["user_role"] = buyer.role.value

    resp = client.post("/cart/add", data={"listing_id": listing.id})
    assert resp.status_code == 400


def test_orders_place_requires_csrf_token(app, client, db_session, make_user):
    app.config["WTF_CSRF_ENABLED"] = True
    buyer = make_user("csrfbuyer2@test.local")

    from app.models.product_listing import ProductListing

    listing = ProductListing(
        seller_id=999,
        title="CSRF Place",
        description="desc",
        category="misc",
        brand="Acme",
        price=15.00,
        condition="new",
        approval_status="approved",
        workflow_status="available",
        is_active=True,
    )
    db_session.add(listing)
    db_session.flush()

    with client.session_transaction() as sess:
        sess["user_id"] = buyer.id
        sess["user_role"] = buyer.role.value

    resp = client.post("/orders/place", data={})
    assert resp.status_code == 400


def test_cart_add_accepts_valid_csrf_token(app, client, db_session, make_user):
    app.config["WTF_CSRF_ENABLED"] = True
    buyer = make_user("csrfbuyer3@test.local")

    from app.models.product_listing import ProductListing

    listing = ProductListing(
        seller_id=999,
        title="CSRF Good",
        description="desc",
        category="misc",
        brand="Acme",
        price=12.00,
        condition="new",
        approval_status="approved",
        workflow_status="available",
        is_active=True,
    )
    db_session.add(listing)
    db_session.flush()

    with client.session_transaction() as sess:
        sess["user_id"] = buyer.id
        sess["user_role"] = buyer.role.value

    token = create_csrf_token(app, client)
    resp = client.post(
        "/cart/add",
        data={"listing_id": listing.id, "csrf_token": token},
    )
    assert resp.status_code == 201


def test_orders_place_accepts_valid_csrf_token(app, client, db_session, make_user):
    app.config["WTF_CSRF_ENABLED"] = True
    buyer = make_user("csrfbuyer4@test.local")

    from app.models.product_listing import ProductListing

    listing = ProductListing(
        seller_id=999,
        title="CSRF Place Good",
        description="desc",
        category="misc",
        brand="Acme",
        price=15.00,
        condition="new",
        approval_status="approved",
        workflow_status="available",
        is_active=True,
    )
    db_session.add(listing)
    db_session.flush()

    with client.session_transaction() as sess:
        sess["user_id"] = buyer.id
        sess["user_role"] = buyer.role.value

    token = create_csrf_token(app, client)
    resp = client.post(
        "/cart/add",
        data={"listing_id": listing.id, "csrf_token": token},
    )
    assert resp.status_code == 201, resp.get_data(as_text=True)

    token = create_csrf_token(app, client)
    resp = client.post(
        "/orders/place",
        data={"csrf_token": token},
    )
    assert resp.status_code == 201, resp.get_data(as_text=True)
