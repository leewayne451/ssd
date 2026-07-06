"""Château Collective — Flask application factory.

create_app() wires the D1 layers together: env-driven configuration
(app/config.py), persistence (SQLAlchemy + Flask-Migrate), the security
cross-cuts (headers/CSP, CSRF, session inactivity timeout), the audit and
security log streams, the web layer (blueprints under app/web/routes) and
the operational CLI (flask seed-admin).
"""

import os
from flask import Flask, request, flash, redirect, url_for, session


from .extensions import db, migrate
from .config import config_map


def create_app(config_name=None):
    """Build and configure the app for `config_name` (development / testing / production; defaults to $FLASK_ENV).
    """
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder="web/templates",
        static_folder="web/static",
    )

    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    cfg_class = config_map.get(config_name)
    if cfg_class is None:
        raise ValueError(
            f"Unknown config name '{config_name}'. "
            f"Valid options: {list(config_map.keys())}"
        )
    app.config.from_object(cfg_class)

    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

    db.init_app(app)
    migrate.init_app(app, db)

    from . import models

    from .logging_config import configure_logging
    configure_logging(app)

    from .security.headers import apply_security_headers
    apply_security_headers(app)

    from .security.csrf import init_csrf
    init_csrf(app)

    from .security.output_encoding import nl2br
    app.jinja_env.filters["nl2br"] = nl2br

    from .web.routes import register_routes
    register_routes(app)

    from .cli import register_cli
    register_cli(app)

    from app.utils.decorators import inject_current_user
    app.context_processor(inject_current_user)

    from app.security.session_policy import check_inactivity_timeout, set_activity_timestamp

    @app.before_request
    def check_session_timeout():
        # Skip for static files and public routes
        if request.endpoint in ['static', 'auth.login', 'auth.register']:
            return
        
        if 'user_id' not in session:
            return
        
        if not check_inactivity_timeout():
            flash('Session timed out due to inactivity.', 'warning')
            return redirect(url_for('auth.login'))

        set_activity_timestamp()

    # Forced first-login rotation quarantine: an account provisioned with a
    # single-use bootstrap password (seed-admin) can reach ONLY the
    # change-password page and logout until it sets its own password. This
    # runs before any view, so admin 2FA enrolment is only reachable after
    # the bootstrap credential has been retired.
    _ROTATION_EXEMPT_ENDPOINTS = {
        None, "static", "auth.change_password_view", "auth.logout", "auth.login",
    }

    @app.before_request
    def enforce_password_rotation():
        if request.endpoint in _ROTATION_EXEMPT_ENDPOINTS:
            return

        from app.security.rbac import load_current_user

        user = load_current_user()
        if user is not None and getattr(user, "must_change_password", False):
            flash("Please set your own password to continue.", "warning")
            return redirect(url_for("auth.change_password_view"))

    return app
