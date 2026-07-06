# dispute_service — dispute lifecycle (FR-17 / SFR-17, D1 UC-06).
#
# A buyer raises a dispute only for their OWN order; administrators review
# and record the outcome (resolved / dismissed) with notes. Buyers see only
# their own disputes; every admin decision writes an AuditLog row
# (FSR-10/11/12, NFSR-08).
import logging
from datetime import datetime, timezone

from app.extensions import db
from app.models.dispute import Dispute
from app.models.enums import DisputeStatus
from app.models.order import Order
from app.services.audit_service import record as audit_record

logger = logging.getLogger(__name__)

MAX_REASON_LENGTH = 2000
MAX_NOTES_LENGTH = 2000

# Statuses an admin may set when closing a dispute.
_CLOSE_STATUSES = {DisputeStatus.RESOLVED.value, DisputeStatus.DISMISSED.value}
_LIVE_STATUSES = (DisputeStatus.OPEN, DisputeStatus.UNDER_REVIEW)


def raise_dispute(buyer, order_id: int, reason: str) -> tuple[Dispute | None, str | None]:
    """
    Open a dispute on `order_id` for `buyer`. Returns (dispute, error).

    SFR-17: ownership is verified server-side — the order must exist AND
    belong to the requester (one generic error for both, no probing).
    One live dispute per order.
    """
    if buyer is None:
        return None, "You must be logged in to raise a dispute."

    order = db.session.get(Order, order_id)
    if order is None or order.buyer_id != buyer.id:
        return None, "Order not found."

    reason = (reason or "").strip()
    if not reason:
        return None, "Please describe the problem with this order."
    if len(reason) > MAX_REASON_LENGTH:
        return None, f"Description is too long (max {MAX_REASON_LENGTH} characters)."

    live = (
        Dispute.query.filter_by(order_id=order.id)
        .filter(Dispute.status.in_(_LIVE_STATUSES))
        .first()
    )
    if live is not None:
        return None, "A dispute for this order is already being handled."

    dispute = Dispute(order_id=order.id, buyer_id=buyer.id, reason=reason)
    db.session.add(dispute)
    db.session.commit()

    audit_record(buyer, "dispute_raised", "dispute", dispute.id,
                 {"order_id": order.id})
    return dispute, None


def get_disputes_for_user(user) -> list[Dispute]:
    """The buyer's own disputes only (SFR-17)."""
    if user is None:
        return []
    return (
        Dispute.query.filter_by(buyer_id=user.id)
        .order_by(Dispute.created_at.desc(), Dispute.id.desc())
        .all()
    )


def get_dispute_for_order(order_id: int) -> Dispute | None:
    return (
        Dispute.query.filter_by(order_id=order_id)
        .order_by(Dispute.created_at.desc(), Dispute.id.desc())
        .first()
    )


def list_open_disputes() -> list[Dispute]:
    """Admin queue — callers must already be role+2FA gated."""
    return (
        Dispute.query.filter(Dispute.status.in_(_LIVE_STATUSES))
        .order_by(Dispute.created_at.asc())
        .all()
    )


def resolve_dispute(admin, dispute_id: int, outcome: str, notes: str = "") -> Dispute:
    """
    Close a dispute as `resolved` or `dismissed` (admin-only surface, FSR-10).

    Raises ValueError on unknown dispute / bad outcome / already closed.
    """
    dispute = db.session.get(Dispute, dispute_id)
    if dispute is None:
        raise ValueError("dispute not found")

    current = getattr(dispute.status, "value", dispute.status)
    if current in _CLOSE_STATUSES:
        raise ValueError("dispute has already been closed")

    if outcome not in _CLOSE_STATUSES:
        raise ValueError("outcome must be 'resolved' or 'dismissed'")

    dispute.status = DisputeStatus(outcome)
    dispute.resolved_by_admin_id = admin.id
    dispute.resolution_notes = (notes or "").strip()[:MAX_NOTES_LENGTH] or None
    dispute.resolved_at = datetime.now(timezone.utc)
    db.session.commit()

    audit_record(admin, "dispute_" + outcome, "dispute", dispute.id,
                 {"order_id": dispute.order_id})
    return dispute
