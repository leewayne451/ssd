from flask import Blueprint, render_template

public_bp = Blueprint("public", __name__)


@public_bp.route("/")
def index():
    return render_template("public/index.html")


@public_bp.route("/healthz")
def healthz():
    return {"status": "ok"}, 200


# Development helper: quick sign-in as a test seller. Only enabled when
# the app is in debug or testing mode so it doesn't expose auth in prod.
from flask import current_app, session, redirect, url_for, flash


@public_bp.route("/dev/login_as_seller")
def dev_login_as_seller():
    app = current_app._get_current_object()
    if not (app.debug or app.config.get("TESTING", False)):
        # Not enabled in production-like environments
        return ("Not allowed", 403)

    # Set session to simulate a logged-in seller
    session["user_id"] = 1
    session["role"] = "seller"
    flash("Signed in as test seller (dev mode).", "info")
    return redirect(url_for("public.index"))
