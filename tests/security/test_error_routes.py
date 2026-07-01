"""
Tests for app/web/routes/error_routes.py

Control under test: 400/403/404/500 are handled by custom, generic pages
and never leak stack traces, exception messages, or other internal detail
to the client.
"""


def test_404_returns_custom_page(client):
    resp = client.get("/this-route-does-not-exist")
    assert resp.status_code == 404
    assert b"Sorry, something went wrong" in resp.data
    # Negative: no default Flask/Werkzeug debug page markers
    assert b"Traceback" not in resp.data
    assert b"werkzeug" not in resp.data.lower()


def test_400_returns_custom_page(client):
    resp = client.get("/trigger-400")
    assert resp.status_code == 400
    assert b"Sorry, something went wrong" in resp.data


def test_403_returns_custom_page(client):
    resp = client.get("/trigger-403")
    assert resp.status_code == 403
    assert b"Sorry, something went wrong" in resp.data


def test_500_returns_generic_page_with_no_leaked_detail(client):
    """Negative/abuse: an unhandled exception containing a sensitive
    internal string (simulated 'secret' / 'password') must never reach
    the client response body. This is the core anti-leak assertion for
    the 500 handler."""
    resp = client.get("/boom")
    assert resp.status_code == 500
    assert b"Sorry, something went wrong" in resp.data

    body_lower = resp.data.lower()
    assert b"runtimeerror" not in body_lower
    assert b"hunter2" not in body_lower
    assert b"traceback" not in body_lower
    assert b"db_password" not in body_lower


def test_error_pages_carry_security_headers(client):
    """Positive: error responses still go through the global headers
    pipeline — security posture doesn't degrade on the unhappy path."""
    resp = client.get("/this-route-does-not-exist")
    assert resp.headers.get("X-Frame-Options") == "DENY"