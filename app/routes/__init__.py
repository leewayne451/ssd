# Routes package — blueprint registration point.
# Phase 0: empty. Blueprints for auth, catalog, cart, admin, etc. added in Phase 1+.
#
# Usage pattern (Phase 1+):
#   from .auth import auth_bp
#   from .catalog import catalog_bp
#
#   def register_blueprints(app):
#       app.register_blueprint(auth_bp)
#       app.register_blueprint(catalog_bp)
#       ...
