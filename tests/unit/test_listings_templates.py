from flask import Flask, render_template_string
import pytest

from jinja2 import Environment, FileSystemLoader


def test_listing_title_is_escaped(tmp_path):
    # Create a minimal Flask app and point to the templates folder
    # Locate the project root (ssd/) so templates can be loaded by Flask/Jinja
    import os
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

    # Create a Flask app configured to use the project's templates folder so
    # template rendering has access to Flask globals like `url_for`.
    templates_root = os.path.join(project_root, 'app', 'web', 'templates')
    app = Flask(__name__, template_folder=templates_root)

    # Malicious title
    listing = {"id": 1, "title": "<script>alert(1)</script>", "price": "9.99", "description": "ok"}

    # Render using the detail template
    # We locate the template path relative to project root: 'ssd/app/web/templates/listings/detail.html'
    # Use a test request context so `url_for` and other request-bound helpers work
    with app.test_request_context():
        tpl = app.jinja_env.get_template('listings/detail.html')
        out = tpl.render(listing=listing)

    assert "<script>alert(1)</script>" not in out
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in out
