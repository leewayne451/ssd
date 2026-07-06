"""Central error pages (NFR-04 / NFSR-21): friendly templates for every
error class — stack traces and internal detail never reach the client.
"""

from flask import Blueprint, render_template

errors_bp = Blueprint("errors", __name__)

@errors_bp.app_errorhandler(400)
def bad_request(e):
    """400 — malformed request."""
    return render_template("errors/400.html"), 400

@errors_bp.app_errorhandler(401)
def unauthorized(e):
    # Friendly sign-in page (Flask-Login used to redirect anonymous browsers;
    # our RBAC returns a bare 401, so the template carries the login link).
    """401 — sign-in required; friendly page with a login link."""
    return render_template("errors/401.html"), 401

@errors_bp.app_errorhandler(403)
def forbidden(e):
    """403 — authenticated but not authorized."""
    return render_template("errors/403.html"), 403

@errors_bp.app_errorhandler(404)
def not_found(e):
    """404 — resource missing (or intentionally hidden)."""
    return render_template("errors/404.html"), 404

@errors_bp.app_errorhandler(500)
def internal_error(e):
    """500 — generic failure page; detail stays in server logs (NFSR-21)."""
    return render_template("errors/500.html"), 500

def register_error_handlers(app):
    """Register the error blueprint with the Flask app."""
    app.register_blueprint(errors_bp)