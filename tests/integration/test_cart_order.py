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
