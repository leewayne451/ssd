"""
Château Collective — Flask extensions
Instantiated here, bound to the app inside create_app() via init_app().
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
