# admin_service — privileged platform operations (FR-12..FR-15).
#
# Every function here is a sensitive admin action: each writes an AuditLog row
# with the acting administrator, timestamp (row default), action type and
# target record (FSR-11/FSR-12/NFSR-08/SFR-13/SFR-15). Routes gate these
# behind role_required("admin") + admin_2fa_required; the services assume an
# already-authorised admin actor and focus on the state change + audit.
import logging

from app.extensions import db
from app.models.authentication_review import AuthenticationReview
from app.models.enums import (
    AccountStatus,
    ApprovalStatus,
    AuthenticationResult,
    WorkflowStatus,
)
from app.models.order import Order
from app.models.product_listing import ProductListing
from app.models.user import User
from app.services import workflow_service
from app.services.audit_service import record as audit_record

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# FR-13 — user suspension
# --------------------------------------------------------------------------

def suspend_user(admin, user_id: int) -> User | None:
    """Suspend a user account. Enforcement (login + live-session denial)
    lives in auth_service / rbac; this flips the status and audits it."""
    user = db.session.get(User, user_id)
    if user is None:
        return None
    user.status = AccountStatus.SUSPENDED
    db.session.commit()
    audit_record(admin, "user_suspended", "user", user.id)
    return user


def unsuspend_user(admin, user_id: int) -> User | None:
    user = db.session.get(User, user_id)
    if user is None:
        return None
    user.status = AccountStatus.ACTIVE
    db.session.commit()
    audit_record(admin, "user_unsuspended", "user", user.id)
    return user


# --------------------------------------------------------------------------
# FR-14 — listing monitoring / approval
# --------------------------------------------------------------------------

def approve_listing(admin, listing_id: int) -> ProductListing | None:
    listing = db.session.get(ProductListing, listing_id)
    if listing is None:
        return None
    listing.approval_status = ApprovalStatus.APPROVED
    listing.reported = False
    db.session.commit()
    audit_record(admin, "listing_approved", "listing", listing.id)
    return listing


def reject_listing(admin, listing_id: int, reason: str = "") -> ProductListing | None:
    listing = db.session.get(ProductListing, listing_id)
    if listing is None:
        return None
    listing.approval_status = ApprovalStatus.REJECTED
    listing.is_active = False
    db.session.commit()
    audit_record(admin, "listing_rejected", "listing", listing.id, {"reason": reason})
    return listing


def report_listing(reporter, listing_id: int, reason: str = "") -> ProductListing | None:
    """Buyer-facing: flag a listing as suspicious for admin review (FR-14).
    Not an admin action, so it records a security event, not an audit row."""
    listing = db.session.get(ProductListing, listing_id)
    if listing is None:
        return None
    listing.reported = True
    listing.report_reason = (reason or "")[:1000]
    db.session.commit()
    try:
        from app.services.security_event_service import record as event_record

        event_record(reporter, "listing_reported", f"listing {listing.id} reported")
    except Exception:  # nosec B110
        logger.debug("failed to record listing_reported event", exc_info=True)
    return listing


# --------------------------------------------------------------------------
# FR-15 — order / workflow status update (uses the audited state machine)
# --------------------------------------------------------------------------

def update_order_workflow(admin, order_id: int, new_status: str) -> Order:
    """Admin drives the workflow through the same validated, audited state
    machine as everyone else — no direct status writes."""
    order = db.session.get(Order, order_id)
    if order is None:
        raise ValueError("order not found")
    return workflow_service.transition_order(order, new_status, admin)


# --------------------------------------------------------------------------
# In-house authentication review (D1 §9.3.5 / THREAT-002)
# --------------------------------------------------------------------------

def record_authentication_review(admin, order_id: int, is_authentic: bool, notes: str = "") -> Order:
    """
    Record the admin's physical-verification outcome and move the order.

    An order must be under_authentication first. Authentic -> authenticated;
    counterfeit -> rejected. Only admins reach here (route-gated), so a seller
    can never authenticate their own item (D1 workflow rule 5).
    """
    order = db.session.get(Order, order_id)
    if order is None:
        raise ValueError("order not found")

    workflow = getattr(order.workflow_status, "value", order.workflow_status)
    if workflow != WorkflowStatus.UNDER_AUTHENTICATION.value:
        raise ValueError("order is not awaiting authentication")

    result = AuthenticationResult.AUTHENTIC if is_authentic else AuthenticationResult.COUNTERFEIT
    review = AuthenticationReview(
        order_id=order.id,
        reviewed_by_admin_id=admin.id,
        result=result,
        notes=(notes or "")[:2000],
    )
    db.session.add(review)
    db.session.commit()

    target_status = (
        WorkflowStatus.AUTHENTICATED.value if is_authentic else WorkflowStatus.REJECTED.value
    )
    workflow_service.transition_order(order, target_status, admin)

    audit_record(
        admin, "authentication_review", "order", order.id,
        {"result": result.value},
    )
    return order
