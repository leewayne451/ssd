from flask import Blueprint, render_template

public_bp = Blueprint("public", __name__)


@public_bp.route("/")
def index():
    return render_template("public/index.html")


@public_bp.route("/healthz")
def healthz():
    return {"status": "ok"}, 200
