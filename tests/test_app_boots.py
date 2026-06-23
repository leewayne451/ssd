"""
Château Collective — Phase 0 smoke tests

Verifies:
  1. create_app("testing") returns a working Flask application instance.
  2. GET /healthz returns HTTP 200 with the expected JSON body.

These are the only behaviours Phase 0 needs to prove.
"""

import json
from app import create_app


def test_create_app_returns_flask_app():
    """create_app('testing') should return a configured Flask application."""
    from flask import Flask

    application = create_app("testing")
    assert isinstance(application, Flask), "create_app() did not return a Flask instance"


def test_app_is_in_testing_mode():
    """The testing config should have TESTING=True and DEBUG=True."""
    application = create_app("testing")
    assert application.config["TESTING"] is True
    assert application.config["DEBUG"] is True


def test_healthz_returns_200(client):
    """GET /healthz should return HTTP 200."""
    response = client.get("/healthz")
    assert response.status_code == 200, (
        f"Expected 200 from /healthz, got {response.status_code}"
    )


def test_healthz_returns_json_status_ok(client):
    """GET /healthz should return JSON body {"status": "ok"}."""
    response = client.get("/healthz")
    data = json.loads(response.data)
    assert data == {"status": "ok"}, f"Unexpected /healthz response body: {data}"


def test_secret_key_is_set(app):
    """SECRET_KEY must be configured (even if it's the test placeholder)."""
    assert app.config.get("SECRET_KEY"), "SECRET_KEY must not be empty"


def test_database_uri_is_in_memory(app):
    """TestingConfig should use an in-memory SQLite database."""
    uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    assert "memory" in uri, (
        f"TestingConfig should use in-memory SQLite, got: {uri}"
    )
