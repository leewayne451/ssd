"""shipment_service — seller shipment updates + tracking (FR-10, D1 UC-05).

Sellers move their own orders awaiting_shipment -> shipped and attach a
tracking reference; buyers see the tracking on their order page. Ownership
is enforced twice: here (fail fast, clear error) and again inside the
workflow state machine that performs the audited transition (SFR-10).
"""
import logging
from datetime import datetime, timezone

from app.extensions import db
from app.models.enums import WorkflowStatus
from app.models.order import Order
from app.models.product_listing import ProductListing
from app.models.shipment import Shipment
from app.services import workflow_service

logger = logging.getLogger(__name__)

MAX_TRACKING_LENGTH = 100


def get_shipment_for_order(order_id: int) -> Shipment | None:
    """The shipment row for an order, or None (unique per order)."""
    return Shipment.query.filter_by(order_id=order_id).first()


def get_sales_for_seller(seller) -> list[tuple[Order, ProductListing, Shipment | None]]:
    """
    All orders placed against the seller's OWN listings, newest first —
    the query is scoped by seller_id, so another seller's orders can never
    appear (FSR-09).
    """
    rows = (
        db.session.query(Order, ProductListing)
        .join(ProductListing, Order.listing_id == ProductListing.id)
        .filter(ProductListing.seller_id == seller.id)
        .order_by(Order.created_at.desc(), Order.id.desc())
        .all()
    )
    return [(order, listing, get_shipment_for_order(order.id)) for order, listing in rows]


def mark_shipped(seller, order_id: int, tracking_number: str) -> Shipment:
    """
    Record the shipment for an order the seller owns and move the workflow
    awaiting_shipment -> shipped (audited by workflow_service).

    Raises ValueError (bad input / wrong state) or PermissionError (not the
    listing's seller — Seller A can never ship Seller B's order, SFR-10).
    """
    order = db.session.get(Order, order_id)
    if order is None:
        raise ValueError("order not found")

    from app.security.ownership import user_owns_order_listing

    if not user_owns_order_listing(order, seller):
        raise PermissionError("you can only update shipments for your own listings")

    tracking_number = (tracking_number or "").strip()
    if not tracking_number:
        raise ValueError("a tracking reference is required")
    if len(tracking_number) > MAX_TRACKING_LENGTH:
        raise ValueError(f"tracking reference is too long (max {MAX_TRACKING_LENGTH} characters)")

    # State + role + ownership re-validated inside the audited state machine;
    # raises before any shipment row is written.
    workflow_service.transition_order(order, WorkflowStatus.SHIPPED.value, seller)

    shipment = get_shipment_for_order(order.id)
    if shipment is None:
        shipment = Shipment(order_id=order.id)
        db.session.add(shipment)
    shipment.tracking_number = tracking_number
    shipment.shipped_at = datetime.now(timezone.utc)
    db.session.commit()

    return shipment
