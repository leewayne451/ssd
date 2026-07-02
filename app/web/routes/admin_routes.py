from flask import Blueprint, render_template, request

from app.security.rbac import role_required
from app.security.admin_2fa import admin_2fa_required
from app.models.audit_log import AuditLog
from app.models.security_event import SecurityEvent

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

@admin_bp.route("/logs")
@role_required("admin")
@admin_2fa_required
def logs():
    """
    Paginated, read-only view of audit log + security events.
    Admin role + 2FA required — same gate as every /admin route.
    """
    page = request.args.get("page", 1, type=int)
    per_page = 20

    audit_logs = AuditLog.query.order_by(
        AuditLog.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)

    security_events = SecurityEvent.query.order_by(
        SecurityEvent.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        "admin/logs.html",
        audit_logs=audit_logs,
        security_events=security_events,
        page=page,
    )
