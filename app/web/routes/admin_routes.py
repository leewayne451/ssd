from flask import Blueprint, render_template

from app.security.rbac import role_required
from app.security.admin_2fa import admin_2fa_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@role_required("admin")
@admin_2fa_required
def index():
    """
    Admin landing page — gated by admin role *and* a verified second factor.

    This is the canonical demonstration of the M2 admin-2FA control. M5 expands
    the admin area (dashboard, log viewer, etc.); any view added to this
    blueprint should keep the ``@role_required("admin")`` + ``@admin_2fa_required``
    decorator pair so the whole /admin surface stays protected.
    """
    return render_template("admin/index.html")

# TODO (M5): admin dashboard, manage users, suspend accounts,
#       approve/reject listings, authentication review workflow,
#       order status updates, resolve disputes, audit logs
