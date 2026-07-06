from flask import Blueprint, render_template

public_bp = Blueprint("public", __name__)


@public_bp.route("/")
def index():
    return render_template("public/index.html")


@public_bp.route("/healthz")
def healthz():
    return {"status": "ok"}, 200


# The old /dev/login_as_seller quick-login helper has been removed outright:
# even a debug-gated authentication bypass is an unacceptable backdoor in a
# security-graded codebase, and tests drive the real /auth/login route via
# the `login_as` fixture instead (see tests/conftest.py).
