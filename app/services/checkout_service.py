# checkout_service — simulated checkout and server-controlled payment states.
#
# D1 §9.3.4: payment is simulated through server-controlled state transitions
#   Pending -> Paid | Failed;  Paid -> Refunded
# The buyer can only INITIATE a payment; the server decides the resulting
# status. No client-supplied payment_status / price / order_status value is
# ever read. No real card data exists anywhere in the system (FSR-17).
import logging
from typing import Dict

from app.extensions import db
from app.models.enums import PaymentStatus, UserRole, WorkflowStatus
from app.models.order import Order
from app.services import workflow_service
from app.security.ownership import user_is_order_buyer

logger = logging.getLogger(__name__)

# Server-side payment state machine (D1 §9.3.4).
PAYMENT_TRANSITIONS: Dict[str, set] = {
    "pending": {"paid", "failed"},
    "paid": {"refunded"},
    "failed": set(),
    "refunded": set(),
}


def can_transition_payment(old: str, new: str) -> bool:
    return new in PAYMENT_TRANSITIONS.get(old, set())


def _audit(actor, action, order, meta=None):
    try:
        from app.services.audit_service import record as audit_record

        audit_record(actor, action, "order", order.id, meta)
    except Exception:  # nosec B110 - logging must never break checkout
        logger.debug("failed to audit %s", action, exc_info=True)


def checkout_order(order: Order, buyer) -> Order:
    """
    Complete the simulated checkout for `order` (FR-11 / SFR-11).

    Only the order's buyer may check out, and only once the item has passed
    in-house authentication (workflow = authenticated) — the core D1 rule
    that no transaction completes before admin verification. On success the
    payment moves pending -> paid and the workflow moves
    authenticated -> sold.

    Raises PermissionError (not the buyer) or ValueError (workflow/payment
    prerequisites not met).
    """
    if buyer is None or not user_is_order_buyer(order, buyer):
        _audit(buyer, "checkout_rejected", order, {"reason": "not_buyer"})
        raise PermissionError("only the order's buyer can check out")

    workflow = (
        order.workflow_status.value
        if hasattr(order.workflow_status, "value")
        else str(order.workflow_status)
    )
    if workflow != WorkflowStatus.AUTHENTICATED.value:
        _audit(buyer, "checkout_rejected", order,
               {"reason": "workflow_not_authenticated", "workflow": workflow})
        raise ValueError(
            "checkout blocked: item has not passed in-house authentication"
        )

    payment = (
        order.payment_status.value
        if hasattr(order.payment_status, "value")
        else str(order.payment_status)
    )
    if not can_transition_payment(payment, PaymentStatus.PAID.value):
        _audit(buyer, "checkout_rejected", order,
               {"reason": "payment_not_pending", "payment": payment})
        raise ValueError(f"checkout blocked: payment is {payment}, not pending")

    # Server decides the payment outcome — the simulated processor approves.
    order.payment_status = PaymentStatus.PAID.value
    db.session.add(order)

    # authenticated -> sold via the audited workflow state machine.
    workflow_service.transition_order(order, WorkflowStatus.SOLD.value, buyer)

    _audit(buyer, "checkout_completed", order,
           {"payment": "paid", "workflow": "sold"})
    return order


def refund_order(order: Order, admin) -> Order:
    """
    Refund a paid order (payment paid -> refunded). Admin-only (D1: the
    seller can never change payment status; buyers cannot self-refund).
    """
    if admin is None or admin.role.value != UserRole.ADMIN.value:
        _audit(admin, "refund_rejected", order, {"reason": "not_admin"})
        raise PermissionError("only administrators can refund an order")

    payment = (
        order.payment_status.value
        if hasattr(order.payment_status, "value")
        else str(order.payment_status)
    )
    if not can_transition_payment(payment, PaymentStatus.REFUNDED.value):
        _audit(admin, "refund_rejected", order, {"reason": "payment_not_paid", "payment": payment})
        raise ValueError(f"cannot refund: payment is {payment}, not paid")

    order.payment_status = PaymentStatus.REFUNDED.value
    db.session.add(order)
    db.session.commit()

    _audit(admin, "order_refunded", order, {"payment": "refunded"})
    return order
