"""Global CSRF protection (FSR-21).

CSRFProtect covers every state-changing route app-wide; templates embed the
token in each form. TestingConfig disables it for test simplicity while
tests/security/test_csrf.py asserts real enforcement.
"""

from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()

def init_csrf(app):
    """Initialise CSRF protection for the app."""
    csrf.init_app(app)
