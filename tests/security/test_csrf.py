"""
Tests for app/security/csrf.py

Control under test: every state-changing (POST/PUT/PATCH/DELETE) request
must carry a valid CSRF token, enforced globally via Flask-WTF's
CSRFProtect (init_csrf).
"""


def test_get_request_does_not_require_csrf_token(client):
    """Positive (sanity check): safe GET requests are never blocked by CSRF
    protection — only state-changing verbs are."""
    resp = client.get("/csrf-form")
    assert resp.status_code == 200
    assert b'name="csrf_token"' in resp.data


def test_post_without_csrf_token_is_rejected(client):
    """Negative/abuse: POSTing the form's own endpoint with no CSRF token
    at all must be rejected (400), proving an attacker-forged cross-site
    POST without the token cannot succeed."""
    resp = client.post("/csrf-form", data={"note": "hello"})
    assert resp.status_code == 400


def test_post_with_garbage_csrf_token_is_rejected(client):
    """Negative/abuse: a malformed/forged token string must also be
    rejected, not just a missing one — guards against an attacker guessing
    or replaying a stale/garbage value."""
    resp = client.post(
        "/csrf-form",
        data={"note": "hello", "csrf_token": "not-a-real-token"},
    )
    assert resp.status_code == 400


def test_post_with_valid_csrf_token_is_accepted(client, csrf_token):
    """Positive: a real token scraped from the rendered form (same client/
    session) is accepted and the request goes through."""
    resp = client.post(
        "/csrf-form",
        data={"note": "hello", "csrf_token": csrf_token},
    )
    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True}


def test_csrf_rejection_response_carries_security_headers(client):
    """Positive: even the 400 CSRF-rejection response still goes through
    the standard security-headers pipeline (no special-case bypass)."""
    resp = client.post("/csrf-form", data={"note": "hello"})
    assert resp.status_code == 400
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"