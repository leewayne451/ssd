"""order_service — business logic for creating orders from a cart.

This module creates Order rows using server-side trusted listing prices,
records status history rows, and clears cart items after successful
placement. It delegates workflow checks to `workflow_service`.
"""
import logging
from typing import List

from app.extensions import db
from app.models.order import Order
from app.models.enums import WorkflowStatus
from app.models.product_listing import ProductListing
from app.models.cart_item import CartItem
from app.services.workflow_service import transition_order
from app.services.audit_service import record as audit_record

logger = logging.getLogger(__name__)


def place_orders_from_cart(user) -> List[Order]:
	"""Create Order rows for each item in the user's cart.

	Uses the server-side `ProductListing.price` as the committed price.
	Returns the list of created Order objects.
	"""
	from app.services.cart_service import get_cart_for_user, clear_cart

	cart = get_cart_for_user(user)
	if not cart or not cart.items:
		return []

	created = []
	for item in list(cart.items):
		listing = ProductListing.query.get(item.listing_id)
		if listing is None:
			# skip missing listings
			continue

		order = Order(
			buyer_id=user.id,
			listing_id=listing.id,
			committed_price=listing.price,
			workflow_status=WorkflowStatus.AVAILABLE,
		)
		db.session.add(order)
		db.session.flush()  # get PK

		# record initial workflow history: available -> committed (creation)
		transition_order(order, "committed", user)

		created.append(order)

	# clear cart after placing orders
	clear_cart(user)

	try:
		audit_record(user, "order_placed", target="order", meta={"count": len(created)})
	except Exception as exc:
		logger.warning("failed to record order_placed audit entry", exc_info=True)

	return created

