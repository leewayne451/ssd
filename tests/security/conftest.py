"""
Shared pytest fixtures for the M6 (secure-coding cross-cuts) test suite.

These tests exercise the *real* cross-cutting helpers
(app.security.headers / app.security.csrf / app.web.routes.error_routes)
against a small purpose-built Flask app that exposes a few trigger routes
(/ping, /csrf-form, /trigger-400, /trigger-403, /boom). Templates used only
by these tests live in tests/security/templates/.
"""
import os

import pytest
from flask import Flask, request, render_template, jsonify, abort

from app.security.headers import apply_security_headers
from app.security.csrf import init_csrf
from app.web.routes.error_routes import errors_bp

HERE = os.path.dirname(os.path.abspath(__file__))


def create_test_app():
    app = Flask(
        "security_tests",
        template_folder=os.path.join(HERE, "templates"),
    )
    app.config.update(
        TESTING=True,
        DEBUG=False,
        PROPAGATE_EXCEPTIONS=False,
        SECRET_KEY="test-secret-key-not-for-prod",
        WTF_CSRF_ENABLED=True,
        SESSION_COOKIE_SECURE=False,  # flips HSTS off in headers.py on purpose
    )

    apply_security_headers(app)
    init_csrf(app)
    app.register_blueprint(errors_bp)

    @app.route("/ping")
    def ping():
        return "pong"

    @app.route("/csrf-form", methods=["GET", "POST"])
    def csrf_form():
        if request.method == "POST":
            return jsonify(ok=True)
        return render_template("csrf_form.html")

    @app.route("/trigger-400")
    def trigger_400():
        abort(400)

    @app.route("/trigger-403")
    def trigger_403():
        abort(403)

    @app.route("/boom")
    def boom():
        raise RuntimeError("super secret internal detail: db_password=hunter2")

    return app


def create_test_app_https():
    app = create_test_app()
    app.config["SESSION_COOKIE_SECURE"] = True
    return app


@pytest.fixture
def app():
    return create_test_app()


@pytest.fixture
def app_https():
    return create_test_app_https()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def client_https(app_https):
    return app_https.test_client()


@pytest.fixture
def csrf_token(client):
    import re
    resp = client.get("/csrf-form")
    assert resp.status_code == 200
    match = re.search(rb'name="csrf_token" value="([^"]+)"', resp.data)
    assert match, "csrf token not found in rendered form"
    return match.group(1).decode()
