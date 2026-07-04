import pytest


def test_place_order_uses_server_side_price(db_session, auth_client, buyer):
    """Ensure a client-supplied price is ignored and the listing price is used."""
    from app.models.product_listing import ProductListing

    # create a listing
    listing = ProductListing(
        seller_id=999,
        title="Widget",
        description="A thing",
        category="gadgets",
        brand="Acme",
        price=19.99,
        condition="new",
        approval_status="approved",
        workflow_status="available",
        is_active=True,
    )
    db_session.add(listing)
    db_session.flush()

    # add to cart via POST
    resp = auth_client.post("/cart/add", json={"listing_id": listing.id, "quantity": 1})
    assert resp.status_code == 201

    # attempt to place order while tampering price in request body (should be ignored)
    resp = auth_client.post("/orders/place", json={"forced_price": 1.23})
    assert resp.status_code == 201
    data = resp.get_json()
    assert "created_order_ids" in data
    assert len(data["created_order_ids"]) == 1

    # load the created order and verify committed_price equals listing.price
    from app.models.order import Order

    oid = data["created_order_ids"][0]
    order = Order.query.get(oid)
    assert float(order.committed_price) == float(listing.price)
    assert order.workflow_status == "committed"


def test_illegal_transition_rejected(db_session, auth_client, buyer):
    from app.models.product_listing import ProductListing
    from app.models.order import Order

    listing = ProductListing(
        seller_id=999,
        title="Gadget",
        description="desc",
        category="gadgets",
        brand="Acme",
        price=9.99,
        condition="new",
        approval_status="approved",
        workflow_status="available",
        is_active=True,
    )
    db_session.add(listing)
    db_session.flush()

    # add then place
    r = auth_client.post("/cart/add", json={"listing_id": listing.id})
    assert r.status_code == 201
    r = auth_client.post("/orders/place")
    assert r.status_code == 201
    oid = r.get_json()["created_order_ids"][0]

    # try illegal jump: committed -> shipped (skipping awaiting_shipment)
    r = auth_client.post(f"/orders/{oid}/status", json={"new_status": "shipped"})
    assert r.status_code == 400
    assert b"illegal workflow transition" in r.get_data()


def test_quantity_persistence_and_update(db_session, client, make_user):
    from app.models.product_listing import ProductListing

    buyer = make_user("qtybuyer@test.local", role=None)
    listing = ProductListing(
        seller_id=999,
        title="QtyItem",
        description="desc",
        category="misc",
        brand="Acme",
        price=5.00,
        condition="new",
        approval_status="approved",
        workflow_status="available",
        is_active=True,
    )
    db_session.add(listing)
    db_session.flush()

    # act as buyer: add quantity 3
    with client.session_transaction() as sess:
        sess["user_id"] = buyer.id
        sess["user_role"] = buyer.role.value if getattr(buyer, 'role', None) else 'buyer'

    r = client.post("/cart/add", json={"listing_id": listing.id, "quantity": 3})
    assert r.status_code == 201

    # view cart and assert quantity shown
    r = client.get("/cart/")
    assert r.status_code == 200
    data = r.get_json()
    assert data and data["items"]
    assert data["items"][0]["quantity"] == 3

    # update quantity to 1
    r = client.post("/cart/update", json={"listing_id": listing.id, "quantity": 1})
    assert r.status_code == 200
    r = client.get("/cart/")
    assert r.get_json()["items"][0]["quantity"] == 1


def test_user_cannot_modify_another_users_order(db_session, client, make_user):
    from app.models.product_listing import ProductListing

    buyer_a = make_user("a@test.local")
    buyer_b = make_user("b@test.local")

    listing = ProductListing(
        seller_id=999,
        title="OwnTest",
        description="desc",
        category="misc",
        brand="Acme",
        price=7.50,
        condition="new",
        approval_status="approved",
        workflow_status="available",
        is_active=True,
    )
    db_session.add(listing)
    db_session.flush()

    # buyer A adds and places order
    with client.session_transaction() as sess:
        sess["user_id"] = buyer_a.id
        sess["user_role"] = buyer_a.role.value if getattr(buyer_a, 'role', None) else 'buyer'
    r = client.post("/cart/add", json={"listing_id": listing.id})
    assert r.status_code == 201
    r = client.post("/orders/place")
    assert r.status_code == 201
    oid = r.get_json()["created_order_ids"][0]

    # buyer B attempts to change order status -> should get 403
    with client.session_transaction() as sess:
        sess["user_id"] = buyer_b.id
        sess["user_role"] = buyer_b.role.value if getattr(buyer_b, 'role', None) else 'buyer'
    r = client.post(f"/orders/{oid}/status", json={"new_status": "awaiting_shipment"})
    assert r.status_code == 403


from app.models.enums import UserRole


def test_seller_can_transition_committed_order(db_session, client, make_user):
    from app.models.product_listing import ProductListing

    buyer = make_user("buyer2@test.local")
    seller = make_user("seller2@test.local", role=UserRole.SELLER)

    listing = ProductListing(
        seller_id=seller.id,
        title="ShipItem",
        description="desc",
        category="misc",
        brand="Acme",
        price=20.00,
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

    r = client.post("/cart/add", json={"listing_id": listing.id})
    assert r.status_code == 201
    r = client.post("/orders/place")
    assert r.status_code == 201
    oid = r.get_json()["created_order_ids"][0]

    with client.session_transaction() as sess:
        sess["user_id"] = seller.id
        sess["user_role"] = seller.role.value

    r = client.post(f"/orders/{oid}/status", json={"new_status": "awaiting_shipment"})
    assert r.status_code == 200
    assert r.get_json()["new_status"] == "awaiting_shipment"
