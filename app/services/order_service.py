# order_service — business logic layer.
import logging
from typing import List

from app.extensions import db
from app.models.enums import WorkflowStatus
from app.models.order import Order
from app.models.order_status_history import OrderStatusHistory
from app.models.product_listing import ProductListing
from app.services.cart_service import get_cart_for_user, clear_cart

logger = logging.getLogger(__name__)


def place_orders_from_cart(user) -> List[Order]:
    """
    Create Order rows for each item in the user's cart.

    Uses the server-side `ProductListing.price` as the committed price.
    Returns the list of created Order objects.
    """
    cart = get_cart_for_user(user)
    if not cart or not cart.items:
        return []

    created = []
    for item in list(cart.items):
        listing = db.session.get(ProductListing, item.listing_id)
        if listing is None:
            # skip missing listings
            continue

        # SFR-09: a buyer can commit only to an approved, active listing —
        # unapproved/deactivated items in a stale cart are skipped.
        approval = getattr(listing.approval_status, "value", listing.approval_status)
        if approval != "approved" or not listing.is_active:
            logger.info("skipping unavailable listing %s at checkout", listing.id)
            continue

        order = Order(
            buyer_id=user.id,
            listing_id=listing.id,
            committed_price=listing.price,
            workflow_status=WorkflowStatus.COMMITTED,
        )
        db.session.add(order)
        db.session.flush()  # get PK

        # record initial workflow history: order committed
        try:
            history = OrderStatusHistory(
                order_id=order.id,
                actor_user_id=user.id,
                old_status="",  # initial state
                new_status=WorkflowStatus.COMMITTED.value,
            )
            db.session.add(history)
            db.session.commit()
        except Exception as exc:
            logger.warning("failed to record order history", exc_info=True)
            db.session.rollback()

        created.append(order)

    # clear cart after placing orders
    clear_cart(user)

    return created
