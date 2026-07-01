"""
XSS-escaping test for the listing detail template.

Renders through the shared `app` fixture (conftest) so blueprints are
registered and url_for('public.index') in base.html resolves.
"""


def test_listing_title_is_escaped(app):
    # Malicious title
    listing = {"id": 1, "title": "<script>alert(1)</script>", "price": "9.99", "description": "ok"}

    with app.test_request_context():
        tpl = app.jinja_env.get_template('listings/detail.html')
        out = tpl.render(listing=listing)

    assert "<script>alert(1)</script>" not in out
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in out
