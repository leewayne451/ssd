"""
Château Collective — Flask extensions
Instantiated here, bound to the app inside create_app() via init_app().

Authentication is deliberately NOT a third-party extension: the module rules
require our own login/session implementation (Flask session + app/security),
so there is no LoginManager here.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()
