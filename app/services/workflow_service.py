# workflow_service — business logic layer.
import logging
from typing import Dict

from app.extensions import db
from app.models.enums import UserRole, WorkflowStatus
from app.models.order import Order
from app.models.order_status_history import OrderStatusHistory

logger = logging.getLogger(__name__)


# Define allowed workflow transitions (from -> set(of allowed next states)).
ALLOWED_TRANSITIONS: Dict[str, set] = {
    "committed": {"awaiting_shipment", "rejected"},
    "awaiting_shipment": {"shipped", "rejected"},
    "shipped": {"sold"},
    "under_authentication": {"authenticated", "rejected"},
    # terminal states present but have no outgoing transitions
    "authenticated": set(),
    "rejected": set(),
    "sold": set(),
}

# Define allowed actor roles for each transition
ALLOWED_ACTOR_ROLES: Dict[str, Dict[str, set[str]]] = {
    "committed": {
        "awaiting_shipment": {UserRole.SELLER.value, UserRole.ADMIN.value},
        "rejected": {UserRole.SELLER.value, UserRole.ADMIN.value},
    },
    "awaiting_shipment": {
        "shipped": {UserRole.SELLER.value, UserRole.ADMIN.value},
        "rejected": {UserRole.SELLER.value, UserRole.ADMIN.value},
    },
    "shipped": {
        "sold": {UserRole.ADMIN.value},
    },
    "under_authentication": {
        "authenticated": {UserRole.ADMIN.value},
        "rejected": {UserRole.ADMIN.value},
    },
}


def can_transition(old: str, new: str) -> bool:
    """Return True when a transition old->new is permitted."""
    allowed = ALLOWED_TRANSITIONS.get(old, set())
    return new in allowed


def is_actor_allowed(old: str, new: str, actor_user) -> bool:
    """Return True when the actor's role is allowed for this transition."""
    if actor_user is None:
        return False
    
    transition_roles = ALLOWED_ACTOR_ROLES.get(old, {}).get(new, set())
    # Admin can always transition
    if actor_user.role.value == UserRole.ADMIN.value:
        return True
    return actor_user.role.value in transition_roles


def transition_order(order: Order, new_status: str, actor_user) -> Order:
    """
    Attempt to transition `order.workflow_status` to `new_status`.

    Records an `OrderStatusHistory` row on success.
    Raises ValueError on illegal transitions or authorization failure.
    """
    old = (
        order.workflow_status.value
        if hasattr(order.workflow_status, "value")
        else str(order.workflow_status)
    )
    
    if not can_transition(old, new_status):
        raise ValueError(f"illegal workflow transition: {old} -> {new_status}")

    if not is_actor_allowed(old, new_status, actor_user):
        raise PermissionError(
            f"role '{actor_user.role.value if actor_user else 'none'}' not authorized for transition {old} -> {new_status}"
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

    return order
