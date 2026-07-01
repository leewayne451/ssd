from app import create_app


def test_listing_title_is_escaped(tmp_path):
    # Use the real application so templates extending base.html can resolve
    # endpoints (e.g. url_for('public.index')) during rendering.
    app = create_app("testing")

    # Malicious title
    listing = {
        "id": 1,
        "title": "<script>alert(1)</script>",
        "price": "9.99",
        "description": "ok",
    }

    with app.test_request_context():
        tpl = app.jinja_env.get_template("listings/detail.html")
        out = tpl.render(listing=listing)

    assert "<script>alert(1)</script>" not in out
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in out
