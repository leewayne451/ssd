"""M6 — friendly 401 page + new-template smoke render (T-39, T-41)."""

import pytest


def test_401_page_renders_with_login_link(client, db_session):
    """T-39: an unauthenticated protected request shows the friendly 401 page."""
    resp = client.get("/cart")
    assert resp.status_code == 401
    assert b"Sign in required" in resp.data
    assert b"/auth/login" in resp.data


@pytest.mark.parametrize("template, context", [
    ("cart/view.html", {"cart": None, "rows": [], "total": 0}),
    ("orders/list.html", {"orders": type("P", (), {"items": []})()}),
    ("admin/users.html", {"users": []}),
    ("admin/listings.html", {"pending": [], "reported": []}),
    ("admin/orders.html", {"awaiting": [], "recent": []}),
])
def test_new_templates_render_without_error(app, template, context):
    """T-41: the templates added this iteration render cleanly (smoke)."""
    with app.test_request_context():
        out = app.jinja_env.get_template(template).render(**context)
    assert out  # non-empty render, no exception
