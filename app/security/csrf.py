from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()

def init_csrf(app):
    """Initialise CSRF protection for the app."""
    csrf.init_app(app)
