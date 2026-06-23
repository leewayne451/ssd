"""
Château Collective — Application Factory
Phase 0: skeleton only. No business logic, auth, or models yet.
"""

import os
from flask import Flask, jsonify

from .extensions import db, migrate
from .config import config_map


def create_app(config_name: str | None = None) -> Flask:
    """
    Application factory.

    Args:
        config_name: One of 'development', 'testing', 'production'.
                     Falls back to the FLASK_ENV environment variable,
                     then to 'development'.
    """
    app = Flask(__name__, instance_relative_config=True)

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    cfg_class = config_map.get(config_name)
    if cfg_class is None:
        raise ValueError(
            f"Unknown config name '{config_name}'. "
            f"Valid options: {list(config_map.keys())}"
        )
    app.config.from_object(cfg_class)

    # Ensure the instance folder exists (SQLite db lives here)
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

    # ------------------------------------------------------------------
    # Extensions
    # ------------------------------------------------------------------
    db.init_app(app)
    migrate.init_app(app, db)

    # ------------------------------------------------------------------
    # Blueprints
    # ------------------------------------------------------------------
    _register_blueprints(app)

    return app


def _register_blueprints(app: Flask) -> None:
    """Register all application blueprints."""
    # Phase 0 placeholder — a single healthcheck blueprint.
    # This will be replaced / extended in Phase 1.
    from flask import Blueprint

    health_bp = Blueprint("health", __name__)

    @health_bp.route("/healthz")
    def healthz():
        return jsonify({"status": "ok"}), 200

    app.register_blueprint(health_bp)
