"""
Tests for app/security/headers.py

Control under test: secure HTTP response headers on every response
(X-Content-Type-Options, X-Frame-Options, Referrer-Policy, CSP, and
conditional HSTS).
"""


def test_security_headers_present_on_every_response(client):
    """Positive: a plain GET response carries all the baseline headers."""
    resp = client.get("/ping")

    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "Content-Security-Policy" in resp.headers


def test_csp_restricts_default_and_script_src(client):
    """Positive: CSP locks scripts/styles down to self + the pinned CDN,
    i.e. it would NOT allow an arbitrary attacker-controlled script host."""
    resp = client.get("/ping")
    csp = resp.headers.get("Content-Security-Policy", "")

    assert "default-src 'self'" in csp
    assert "script-src 'self' https://cdn.jsdelivr.net" in csp
    # Negative: no wildcard script source and no inline-script allowance
    assert "script-src *" not in csp
    assert "unsafe-inline" not in csp


def test_hsts_absent_over_plain_http_config(client):
    """Negative: when SESSION_COOKIE_SECURE is False (i.e. the app is not
    configured for HTTPS), HSTS must NOT be sent — sending it without TLS
    would be actively wrong (forces HTTPS the app can't serve)."""
    resp = client.get("/ping")
    assert "Strict-Transport-Security" not in resp.headers


def test_hsts_present_when_cookie_secure_is_true(client_https):
    """Positive: once the app is configured for HTTPS (SESSION_COOKIE_SECURE
    True, mirroring prod config), HSTS is sent with a 1-year max-age and
    includeSubDomains."""
    resp = client_https.get("/ping")
    hsts = resp.headers.get("Strict-Transport-Security")

    assert hsts is not None
    assert "max-age=31536000" in hsts
    assert "includeSubDomains" in hsts


def test_headers_present_on_error_responses_too(client):
    """Positive: security headers are applied via after_request, so they
    must also be present on non-200 / error responses, not just happy-path
    ones."""
    resp = client.get("/does-not-exist")
    assert resp.status_code == 404
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"