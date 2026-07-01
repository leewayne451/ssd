from app import create_app


def _get_app_with_templates():
    # Use the real application so templates extending base.html can resolve
    # endpoints (e.g. url_for('public.index')) during rendering.
    return create_app("testing")


def test_index_title_is_escaped():
    app = _get_app_with_templates()
    listings = [{"id": 1, "title": "<script>alert(1)</script>", "price": "9.99"}]

    with app.test_request_context():
        tpl = app.jinja_env.get_template("listings/index.html")
        out = tpl.render(listings=listings)

    assert "<script>alert(1)</script>" not in out
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in out


def test_form_fields_are_escaped(app):
    listing = {
        "id": 1,
        "title": "<img src=x onerror=alert(1)>",
        "description": "<b>bold</b>",
        "price": "9.99",
    }

    with app.test_request_context():
        tpl = app.jinja_env.get_template("listings/form.html")
        out = tpl.render(listing=listing)

    # Title should be escaped inside the input value
    assert "<img src=x onerror=alert(1)>" not in out
    assert "&lt;img src=x onerror=alert(1)&gt;" in out

    # Description should be escaped inside the textarea
    assert "<b>bold</b>" not in out
    assert "&lt;b&gt;bold&lt;/b&gt;" in out
