import os
from flask import Flask, request, flash, redirect, url_for, session


from .extensions import db, migrate
from .config import config_map


def create_app(config_name=None):
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

    return app
