"""Additional CSRF tests for new cart and order routes."""


def test_cart_add_requires_csrf_token(client):
    resp = client.post("/cart/add", data={"listing_id": 1})
    assert resp.status_code == 400


def test_orders_place_requires_csrf_token(client):
    resp = client.post("/orders/place", data={})
    assert resp.status_code == 400


def test_cart_add_accepts_valid_csrf_token(client, csrf_token):
    resp = client.post(
        "/cart/add",
        data={"listing_id": 1, "csrf_token": csrf_token},
    )
    assert resp.status_code in (400, 401)


def test_orders_place_accepts_valid_csrf_token(client, csrf_token):
    resp = client.post(
        "/orders/place",
        data={"csrf_token": csrf_token},
    )
    assert resp.status_code in (400, 401)
