"""
Château Collective — Pytest fixtures (Phase 0)

Provides:
  - app     : configured Flask application in testing mode
  - client  : Flask test client
  - db_session : SQLAlchemy session scoped to each test (ready for Phase 1 models)
"""

import pytest
from app import create_app
from app.extensions import db as _db


@pytest.fixture(scope="session")
def app():
    """
    Create a Flask application configured for the test suite.
    Session-scoped so the app is created once per test run.
    """
    flask_app = create_app("testing")

    # Push an application context for the duration of the session
    ctx = flask_app.app_context()
    ctx.push()

    # Create all tables (no-op in Phase 0 — no models yet, but safe to call)
    _db.create_all()

    yield flask_app

    # Teardown
    _db.drop_all()
    ctx.pop()


@pytest.fixture()
def client(app):
    """
    Flask test client.
    Function-scoped so each test gets a fresh client with a clean cookie jar.
    """
    return app.test_client()


@pytest.fixture()
def db_session(app):
    """
    SQLAlchemy database session, rolled back after each test to keep
    tests isolated. Ready to use in Phase 1+ once models exist.
    """
    connection = _db.engine.connect()
    transaction = connection.begin()

    # Bind the session to the connection so all queries run inside the transaction
    _db.session.bind = connection  # type: ignore[attr-defined]

    yield _db.session

    _db.session.remove()
    transaction.rollback()
    connection.close()
