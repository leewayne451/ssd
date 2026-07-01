from flask import url_for

from .public_routes import public_bp
from .auth_routes import auth_bp
from .profile_routes import profile_bp
from .seller_routes import seller_bp
from .listing_routes import listing_bp
from .cart_routes import cart_bp
from .order_routes import order_bp
from .shipment_routes import shipment_bp
from .review_routes import review_bp
from .dispute_routes import dispute_bp
from .admin_routes import admin_bp
from .admin_2fa_routes import admin_2fa_bp
from .error_routes import register_error_handlers


def register_routes(app):
    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(seller_bp)
    app.register_blueprint(listing_bp)

    @app.context_processor
    def inject_nav_urls():
        return {
            'home_url': url_for('public.index'),
            'create_listing_url': url_for('listing.create'),
            'auth_login_url': url_for('auth.login'),
            'auth_register_url': url_for('auth.register'),
            'auth_logout_url': url_for('auth.logout'),
        }

    # Register helper to fetch uploads for templates
    from app.models.uploaded_file import UploadedFile

    def _get_listing_uploads(listing_id):
        try:
            return UploadedFile.query.filter_by(listing_id=listing_id).all()
        except Exception:
            return []

    app.jinja_env.globals['get_listing_uploads'] = _get_listing_uploads
    app.register_blueprint(cart_bp)
    app.register_blueprint(order_bp)
    app.register_blueprint(shipment_bp)
    app.register_blueprint(review_bp)
    app.register_blueprint(dispute_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(admin_2fa_bp)
    register_error_handlers(app)
