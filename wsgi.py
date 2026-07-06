"""Production WSGI entrypoint — Gunicorn imports `app` from here; ProxyFix
makes Flask trust nginx's X-Forwarded-* headers (details below).
"""

from werkzeug.middleware.proxy_fix import ProxyFix

from app import create_app

app = create_app()

# The app runs behind nginx (which terminates TLS). ProxyFix makes Flask trust
# the X-Forwarded-* headers nginx sets, so it sees the real client IP and knows
# the original request was HTTPS. Required for correct Secure-cookie behaviour,
# url_for(_external=True), and accurate client IPs in the audit log. Applied only
# on the deployed WSGI entrypoint — tests import create_app directly and are
# unaffected.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
