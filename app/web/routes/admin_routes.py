from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify

from app.security.rbac import role_required
from app.security.admin_2fa import admin_2fa_required
from app.models.audit_log import AuditLog
from app.models.security_event import SecurityEvent
from app.models.user import User
from app.models.product_listing import ProductListing
from app.models.order import Order
from app.models.enums import ApprovalStatus, WorkflowStatus
from app.services import admin_service, dispute_service, seller_service
from app.services.auth_service import get_current_user

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

# Every route in this blueprint carries role_required("admin") + admin_2fa_required.
_VALID_WORKFLOW_VALUES = {s.value for s in WorkflowStatus}

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


# --- FR-13: user management / suspension ----------------------------------

@admin_bp.route("/users")
@role_required("admin")
@admin_2fa_required
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=all_users)


@admin_bp.route("/users/<int:user_id>/suspend", methods=["POST"])
@role_required("admin")
@admin_2fa_required
def suspend_user(user_id):
    admin = get_current_user()
    if admin_service.suspend_user(admin, user_id) is None:
        flash("User not found.", "danger")
    else:
        flash("User suspended.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/unsuspend", methods=["POST"])
@role_required("admin")
@admin_2fa_required
def unsuspend_user(user_id):
    admin = get_current_user()
    if admin_service.unsuspend_user(admin, user_id) is None:
        flash("User not found.", "danger")
    else:
        flash("User reactivated.", "success")
    return redirect(url_for("admin.users"))


# --- FR-14: listing monitoring / approval ---------------------------------

@admin_bp.route("/listings")
@role_required("admin")
@admin_2fa_required
def listings():
    pending = ProductListing.query.filter_by(approval_status=ApprovalStatus.PENDING).all()
    reported = ProductListing.query.filter_by(reported=True).all()
    return render_template("admin/listings.html", pending=pending, reported=reported)


@admin_bp.route("/listings/<int:listing_id>/approve", methods=["POST"])
@role_required("admin")
@admin_2fa_required
def approve_listing(listing_id):
    admin = get_current_user()
    if admin_service.approve_listing(admin, listing_id) is None:
        flash("Listing not found.", "danger")
    else:
        flash("Listing approved.", "success")
    return redirect(url_for("admin.listings"))


@admin_bp.route("/listings/<int:listing_id>/reject", methods=["POST"])
@role_required("admin")
@admin_2fa_required
def reject_listing(listing_id):
    admin = get_current_user()
    reason = request.form.get("reason", "")
    if admin_service.reject_listing(admin, listing_id, reason) is None:
        flash("Listing not found.", "danger")
    else:
        flash("Listing rejected.", "success")
    return redirect(url_for("admin.listings"))


# --- FR-04 / SFR-04: seller application review -----------------------------

@admin_bp.route("/seller-applications")
@role_required("admin")
@admin_2fa_required
def seller_applications():
    pending = seller_service.list_pending_applications()
    return render_template("admin/seller_applications.html", pending=pending)


@admin_bp.route("/seller-applications/<int:application_id>/approve", methods=["POST"])
@role_required("admin")
@admin_2fa_required
def approve_seller_application(application_id):
    admin = get_current_user()
    try:
        seller_service.approve_application(admin, application_id)
        flash("Application approved — the user is now a verified seller.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    return redirect(url_for("admin.seller_applications"))


@admin_bp.route("/seller-applications/<int:application_id>/reject", methods=["POST"])
@role_required("admin")
@admin_2fa_required
def reject_seller_application(application_id):
    admin = get_current_user()
    try:
        seller_service.reject_application(admin, application_id)
        flash("Application rejected.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    return redirect(url_for("admin.seller_applications"))


# --- FR-15 + authentication review: order/workflow management -------------

@admin_bp.route("/orders")
@role_required("admin")
@admin_2fa_required
def orders():
    awaiting = Order.query.filter_by(
        workflow_status=WorkflowStatus.UNDER_AUTHENTICATION
    ).all()
    recent = Order.query.order_by(Order.created_at.desc()).limit(50).all()
    return render_template("admin/orders.html", awaiting=awaiting, recent=recent)


@admin_bp.route("/orders/<int:order_id>/status", methods=["POST"])
@role_required("admin")
@admin_2fa_required
def update_order_status(order_id):
    admin = get_current_user()
    new_status = request.form.get("new_status", "")
    if new_status not in _VALID_WORKFLOW_VALUES:
        flash("Invalid workflow status.", "danger")
        return redirect(url_for("admin.orders"))
    try:
        admin_service.update_order_workflow(admin, order_id, new_status)
        flash("Order workflow updated.", "success")
    except (ValueError, PermissionError) as e:
        flash(str(e), "danger")
    return redirect(url_for("admin.orders"))


# --- FR-17 / SFR-17: dispute resolution ------------------------------------

@admin_bp.route("/disputes")
@role_required("admin")
@admin_2fa_required
def disputes():
    open_disputes = dispute_service.list_open_disputes()
    return render_template("admin/disputes.html", open_disputes=open_disputes)


@admin_bp.route("/disputes/<int:dispute_id>/resolve", methods=["POST"])
@role_required("admin")
@admin_2fa_required
def resolve_dispute(dispute_id):
    admin = get_current_user()
    outcome = request.form.get("outcome", "")
    notes = request.form.get("notes", "")
    try:
        dispute_service.resolve_dispute(admin, dispute_id, outcome, notes)
        flash(f"Dispute {outcome}.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    return redirect(url_for("admin.disputes"))


@admin_bp.route("/orders/<int:order_id>/authenticate", methods=["POST"])
@role_required("admin")
@admin_2fa_required
def authenticate_order(order_id):
    """In-house authentication outcome (D1 §9.3.5)."""
    admin = get_current_user()
    outcome = request.form.get("outcome", "")
    notes = request.form.get("notes", "")
    if outcome not in {"authentic", "counterfeit"}:
        flash("Choose an authentication outcome.", "danger")
        return redirect(url_for("admin.orders"))
    try:
        admin_service.record_authentication_review(
            admin, order_id, is_authentic=(outcome == "authentic"), notes=notes
        )
        flash(f"Authentication recorded: {outcome}.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    return redirect(url_for("admin.orders"))
