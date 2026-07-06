# seller_service — seller application lifecycle (FR-04 / SFR-04, D1 UC-02).
#
# A registered buyer applies to become a verified seller; an administrator
# reviews the application and approves (promoting the account to the seller
# role) or rejects it. Application details are confidential: services expose
# them only per-applicant or to the admin queue, and the routes gate those
# surfaces with ownership / role+2FA checks (SFR-04).
import logging
from datetime import datetime, timezone

from app.extensions import db
from app.models.enums import ApprovalStatus, UserRole
from app.models.seller_application import SellerApplication
from app.models.user import User
from app.services.audit_service import record as audit_record

logger = logging.getLogger(__name__)

MAX_REASON_LENGTH = 2000


def apply_to_become_seller(user, reason: str) -> tuple[SellerApplication | None, str | None]:
    """
    Create a seller application for `user`. Returns (application, error).

    Server-side rules (never trusted to the form):
      * only buyer accounts may apply — sellers/admins have nothing to gain;
      * the stated reason is required and length-capped (SDR-01);
      * one live (pending) application per user, and an approved application
        can never be duplicated.
    """
    if user is None:
        return None, "You must be logged in to apply."

    if user.role.value != UserRole.BUYER.value:
        return None, "Only buyer accounts can apply to become a seller."

    reason = (reason or "").strip()
    if not reason:
        return None, "Please describe why you want to sell on the platform."
    if len(reason) > MAX_REASON_LENGTH:
        return None, f"Reason is too long (max {MAX_REASON_LENGTH} characters)."

    existing = (
        SellerApplication.query.filter_by(user_id=user.id)
        .filter(SellerApplication.status.in_(
            [ApprovalStatus.PENDING, ApprovalStatus.APPROVED]
        ))
        .first()
    )
    if existing is not None:
        if existing.status == ApprovalStatus.PENDING:
            return None, "You already have an application under review."
        return None, "Your application was already approved."

    application = SellerApplication(user_id=user.id, reason=reason)
    db.session.add(application)
    db.session.commit()

    audit_record(user, "seller_application_submitted", "seller_application", application.id)
    return application, None


def get_latest_application_for_user(user) -> SellerApplication | None:
    """The applicant's own view of their newest application (SFR-04)."""
    if user is None:
        return None
    return (
        SellerApplication.query.filter_by(user_id=user.id)
        .order_by(SellerApplication.created_at.desc(), SellerApplication.id.desc())
        .first()
    )


def list_pending_applications() -> list[SellerApplication]:
    """Admin review queue — callers must already be role+2FA gated."""
    return (
        SellerApplication.query.filter_by(status=ApprovalStatus.PENDING)
        .order_by(SellerApplication.created_at.asc())
        .all()
    )


def _load_pending(application_id: int) -> SellerApplication:
    application = db.session.get(SellerApplication, application_id)
    if application is None:
        raise ValueError("application not found")
    if application.status != ApprovalStatus.PENDING:
        raise ValueError("application has already been reviewed")
    return application


def approve_application(admin, application_id: int) -> SellerApplication:
    """
    Approve a pending application and promote the applicant to seller.

    The role change happens here, server-side, off the DB row — the applicant
    gains seller capability on their next request (rbac reads the DB role).
    Audited with actor, target and outcome (FSR-11/12).
    """
    application = _load_pending(application_id)

    applicant = db.session.get(User, application.user_id)
    if applicant is None:
        raise ValueError("applicant account no longer exists")

    application.status = ApprovalStatus.APPROVED
    application.reviewed_by_admin_id = admin.id
    application.reviewed_at = datetime.now(timezone.utc)
    applicant.role = UserRole.SELLER
    db.session.commit()

    audit_record(
        admin, "seller_application_approved", "seller_application", application.id,
        {"applicant_user_id": applicant.id},
    )
    return application


def reject_application(admin, application_id: int) -> SellerApplication:
    """Reject a pending application (applicant keeps the buyer role)."""
    application = _load_pending(application_id)

    application.status = ApprovalStatus.REJECTED
    application.reviewed_by_admin_id = admin.id
    application.reviewed_at = datetime.now(timezone.utc)
    db.session.commit()

    audit_record(
        admin, "seller_application_rejected", "seller_application", application.id,
        {"applicant_user_id": application.user_id},
    )
    return application
