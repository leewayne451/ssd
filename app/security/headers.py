"""Security response headers on every response (FSR-20 / D1 9.3.7).

CSP is locked to 'self' for scripts/styles/fonts (Bootstrap is self-hosted;
no inline script or style executes), plus clickjacking and MIME-sniffing
defences, referrer policy, and HSTS only when the app is HTTPS-configured.
"""

def apply_security_headers(app):
    """Register the after_request hook that stamps the security headers onto every response, error pages included.
    """
    @app.after_request
    def set_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Bootstrap is self-hosted (app/web/static/vendor/), so every source
        # list stays 'self' — no third-party script/style host is trusted.
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data:; "
            "font-src 'self'"
        )
        # HSTS — only sent over HTTPS; browsers will refuse HTTP for 1 year
        if app.config.get("SESSION_COOKIE_SECURE", False):
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response
