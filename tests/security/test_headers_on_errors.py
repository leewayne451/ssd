"""
Security headers on error/non-200 responses.

Control under test: since nginx no longer duplicates security headers, the
application (app/security/headers.py, via after_request) is the single source
— so error paths (404/403/500) must carry them too, or a misconfigured route
would silently lose protection (AI review finding F1 on PR #70).

Uses the same purpose-built app/fixtures as test_error_routes.py
(tests/security/conftest.py provides /trigger-403 and /boom).
"""

# HSTS is intentionally absent here: it is only sent when
# SESSION_COOKIE_SECURE is enabled (production), not in the test config.
ALWAYS_ON_HEADERS = [
    "X-Content-Type-Options",
    "X-Frame-Options",
    "Referrer-Policy",
    "Content-Security-Policy",
]


def _assert_security_headers(resp):
    for header in ALWAYS_ON_HEADERS:
        assert header in resp.headers, (
            f"{header} missing on {resp.status_code} response — "
            "app/security/headers.py is the sole header source; "
            "error paths must be covered"
        )


def test_headers_present_on_404(client):
    resp = client.get("/this-route-does-not-exist")
    assert resp.status_code == 404
    _assert_security_headers(resp)


def test_headers_present_on_403(client):
    resp = client.get("/trigger-403")
    assert resp.status_code == 403
    _assert_security_headers(resp)


def test_headers_present_on_500(client):
    resp = client.get("/boom")
    assert resp.status_code == 500
    _assert_security_headers(resp)
