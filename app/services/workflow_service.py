# workflow_service — server-side order workflow state machine (D1 §9.4 / H-3).
#
# The transition map below is the EXACT flow from Deliverable One:
#
#   Committed -> Awaiting Shipment -> Shipped -> Under Authentication
#       -> Authenticated -> Sold        (buyer completes simulated checkout)
#       -> Rejected                     (admin rejects authentication)
#
# There is deliberately NO shipped -> sold edge: an order can never complete
# without passing the in-house authentication step — that is the platform's
# core control. Client-submitted workflow values are never trusted; every
# transition is validated here (state, role, ownership) and audited.
import logging
from typing import Dict

from app.extensions import db
from app.models.enums import UserRole, WorkflowStatus
from app.models.order import Order
from app.models.order_status_history import OrderStatusHistory

logger = logging.getLogger(__name__)


# Allowed workflow transitions (from -> set(of allowed next states)) — D1 H-3.
# committed/awaiting_shipment -> rejected are the admin "workflow compliance"
# rejection edges (H-3: Rejected = fails authentication OR compliance).
ALLOWED_TRANSITIONS: Dict[str, set] = {
    "committed": {"awaiting_shipment", "rejected"},
    "awaiting_shipment": {"shipped", "rejected"},
    "shipped": {"under_authentication"},
    "under_authentication": {"authenticated", "rejected"},
    "authenticated": {"sold"},
    # terminal states have no outgoing transitions
    "rejected": set(),
    "sold": set(),
}

# Allowed actor roles for each transition. Ownership is enforced on top of
# this in transition_order(): sellers must own the order's listing, buyers
# must be the order's buyer; admins are exempt from ownership.
ALLOWED_ACTOR_ROLES: Dict[str, Dict[str, set]] = {
    "committed": {
        "awaiting_shipment": {UserRole.SELLER.value, UserRole.ADMIN.value},
        "rejected": {UserRole.ADMIN.value},
    },
    "awaiting_shipment": {
        "shipped": {UserRole.SELLER.value, UserRole.ADMIN.value},
        "rejected": {UserRole.ADMIN.value},
    },
    "shipped": {
        "under_authentication": {UserRole.ADMIN.value},
    },
    "under_authentication": {
        "authenticated": {UserRole.ADMIN.value},
        "rejected": {UserRole.ADMIN.value},
    },
    "authenticated": {
        "sold": {UserRole.BUYER.value, UserRole.ADMIN.value},
    },
}

_VALID_STATUS_VALUES = {status.value for status in WorkflowStatus}


def can_transition(old: str, new: str) -> bool:
    """Return True when a transition old->new is permitted."""
    allowed = ALLOWED_TRANSITIONS.get(old, set())
    return new in allowed


def is_actor_allowed(old: str, new: str, actor_user) -> bool:
    """Return True when the actor's role is allowed for this transition."""
    if actor_user is None:
        return False

    transition_roles = ALLOWED_ACTOR_ROLES.get(old, {}).get(new, set())
    # Admin can always perform an allowed transition
    if actor_user.role.value == UserRole.ADMIN.value:
        return True
    return actor_user.role.value in transition_roles


def _actor_owns_transition(order: Order, old: str, new: str, actor_user) -> bool:
    """
    Ownership on top of the role check (CTRL-002):
      * seller actors must be the seller of the order's LISTING —
        Seller A can never move Seller B's order;
      * buyer actors must be the order's buyer;
      * admins are exempt.
    """
    from app.security.ownership import user_is_order_buyer, user_owns_order_listing

    role = actor_user.role.value
    if role == UserRole.ADMIN.value:
        return True
    if role == UserRole.SELLER.value:
        return user_owns_order_listing(order, actor_user)
    if role == UserRole.BUYER.value:
        return user_is_order_buyer(order, actor_user)
    return False


def _record_rejected_attempt(order: Order, old: str, new: str, actor_user, reason: str):
    """Audit + security-event every rejected transition attempt. Never raises."""
    try:
        from app.services.audit_service import record as audit_record
        from app.services.security_event_service import record as event_record

        audit_record(
            actor_user, "workflow_transition_rejected", "order", order.id,
            {"from": old, "to": new, "reason": reason},
        )
        event_record(
            actor_user, "workflow_transition_rejected",
            f"order {order.id}: {old} -> {new} ({reason})",
        )
    except Exception:  # nosec B110 - logging must never break the caller
        logger.debug("failed to record rejected workflow attempt", exc_info=True)


def transition_order(order: Order, new_status: str, actor_user) -> Order:
    """
    Attempt to transition `order.workflow_status` to `new_status`.

    Validates, in order: the status value itself, the state-machine edge,
    the actor's role, and the actor's ownership of the order. Records an
    `OrderStatusHistory` row AND an `AuditLog` row on success (FSR-11/12,
    NFSR-08); rejected attempts are audited as security events.

    Raises ValueError on illegal transitions, PermissionError on
    authorization failure.
    """
    old = (
        order.workflow_status.value
        if hasattr(order.workflow_status, "value")
        else str(order.workflow_status)
    )

    if new_status not in _VALID_STATUS_VALUES:
        _record_rejected_attempt(order, old, str(new_status), actor_user, "unknown_status")
        raise ValueError(f"unknown workflow status: {new_status!r}")

    if not can_transition(old, new_status):
        _record_rejected_attempt(order, old, new_status, actor_user, "illegal_transition")
        raise ValueError(f"illegal workflow transition: {old} -> {new_status}")

    if not is_actor_allowed(old, new_status, actor_user):
        _record_rejected_attempt(order, old, new_status, actor_user, "role_not_allowed")
        raise PermissionError(
            f"role '{actor_user.role.value if actor_user else 'none'}' not authorized "
            f"for transition {old} -> {new_status}"
        )

    if not _actor_owns_transition(order, old, new_status, actor_user):
        _record_rejected_attempt(order, old, new_status, actor_user, "not_owner")
        raise PermissionError(
            f"actor does not own order {order.id} for transition {old} -> {new_status}"
        )

    # perform transition
    order.workflow_status = new_status
    db.session.add(order)

    history = OrderStatusHistory(
        order_id=order.id,
        actor_user_id=actor_user.id if actor_user else None,
        old_status=old,
        new_status=new_status,
    )
    db.session.add(history)
    db.session.commit()

    # D1 workflow security rule 9: important workflow changes are recorded in
    # audit logs with actor, old state, new state and target record.
    try:
        from app.services.audit_service import record as audit_record

        audit_record(
            actor_user, "workflow_transition", "order", order.id,
            {"from": old, "to": new_status},
        )
    except Exception:  # nosec B110
        logger.debug("failed to audit workflow transition", exc_info=True)

    return order
