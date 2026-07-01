from flask import Blueprint, render_template

errors_bp = Blueprint("errors", __name__)

@errors_bp.app_errorhandler(400)
def bad_request(e):
    return render_template("errors/400.html"), 400

@errors_bp.app_errorhandler(403)
def forbidden(e):
    return render_template("errors/403.html"), 403

@errors_bp.app_errorhandler(404)
def not_found(e):
    return render_template("errors/404.html"), 404

@errors_bp.app_errorhandler(500)
def internal_error(e):
    return render_template("errors/500.html"), 500

def register_error_handlers(app):
    """Register the error blueprint with the Flask app."""
    app.register_blueprint(errors_bp)