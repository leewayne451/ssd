from typing import Dict

from app.extensions import db
from app.models.order import Order
from app.models.order_status_history import OrderStatusHistory
from app.services.audit_service import record as audit_record


# Define allowed workflow transitions (from -> set(of allowed next states)).
# These are simplified for Phase 1 and can be extended later.
ALLOWED_TRANSITIONS: Dict[str, set] = {
    "committed": {"awaiting_shipment", "rejected"},
    "awaiting_shipment": {"shipped", "rejected"},
    "shipped": {"sold"},
    "under_authentication": {"authenticated", "rejected"},
    # terminal states present but have no outgoing transitions
    "authenticated": set(),
    "rejected": set(),
    "sold": set(),
    "available": {"committed"},
}


def can_transition(old: str, new: str) -> bool:
    """Return True when a transition old->new is permitted."""
    allowed = ALLOWED_TRANSITIONS.get(old, set())
    return new in allowed


def transition_order(order: Order, new_status: str, actor_user) -> Order:
    """Attempt to transition `order.workflow_status` to `new_status`.

    Records an `OrderStatusHistory` row and an audit entry on success.
    Raises ValueError on illegal transitions.
    """
    old = order.workflow_status.value if hasattr(order.workflow_status, "value") else str(order.workflow_status)
    if not can_transition(old, new_status):
        raise ValueError(f"illegal workflow transition: {old} -> {new_status}")

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

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    # audit the change (best-effort)
    try:
        audit_record(actor_user, "order_status_changed", target="order", target_id=order.id, meta={"old": old, "new": new_status})
    except Exception:
        # swallow audit errors
        pass

    return order
# workflow_service — business logic layer.
