"""cart_service — business logic layer for cart operations.

Implements basic add/remove/view operations with ownership checks and
server-side validation (quantity bounds, listing existence). This is a
minimal, phase-1 implementation supporting E4/4.1.
"""
from typing import Optional

from app.extensions import db
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.product_listing import ProductListing
from app.security.input_validation import validate_integer_range


def get_or_create_cart_for_user(user) -> Cart:
	"""Return the Cart for `user`, creating one if needed."""
	cart = Cart.query.filter_by(buyer_id=user.id).one_or_none()
	if cart:
		return cart
	cart = Cart(buyer_id=user.id)
	db.session.add(cart)
	db.session.commit()
	return cart


def get_cart_for_user(user) -> Optional[Cart]:
	return Cart.query.filter_by(buyer_id=user.id).one_or_none()


def add_item(user, listing_id, quantity=1) -> CartItem:
	"""Add a listing to the user's cart.

	Args:
		user: current_user object
		listing_id: id of ProductListing to add
		quantity: requested quantity (validated server-side)

	Returns:
		The created or existing CartItem.

	Raises:
		ValueError on invalid input (missing listing, invalid quantity).
	"""
	ok, err = validate_integer_range(quantity, "Quantity", min_val=1, max_val=100)
	if not ok:
		raise ValueError(err)

	# Ensure the listing exists and take server-side price from it (do not trust client)
	listing = ProductListing.query.get(listing_id)
	if listing is None:
		raise ValueError("listing not found")

	cart = get_or_create_cart_for_user(user)

	# Idempotent: create or update quantity for existing cart item
	item = CartItem.query.filter_by(cart_id=cart.id, listing_id=listing.id).one_or_none()
	if item is None:
		item = CartItem(cart_id=cart.id, listing_id=listing.id, quantity=int(quantity))
		db.session.add(item)
	else:
		# increment existing quantity but enforce server-side cap
		new_qty = min(100, item.quantity + int(quantity))
		item.quantity = new_qty

	db.session.commit()

	return item


def remove_item(user, listing_id) -> bool:
	"""Remove a listing from the user's cart. Returns True when removed."""
	cart = get_cart_for_user(user)
	if not cart:
		return False
	item = CartItem.query.filter_by(cart_id=cart.id, listing_id=listing_id).one_or_none()
	if not item:
		return False
	db.session.delete(item)
	db.session.commit()
	return True


def clear_cart(user) -> None:
	cart = get_cart_for_user(user)
	if not cart:
		return
	CartItem.query.filter_by(cart_id=cart.id).delete()
	db.session.commit()


def update_item_quantity(user, listing_id, quantity) -> bool:
	"""Set the quantity for a cart item. If quantity <= 0, remove the item."""
	ok, err = validate_integer_range(quantity, "Quantity", min_val=0, max_val=100)
	if not ok:
		raise ValueError(err)

	cart = get_cart_for_user(user)
	if not cart:
		return False
	item = CartItem.query.filter_by(cart_id=cart.id, listing_id=listing_id).one_or_none()
	if not item:
		return False

	q = int(quantity)
	if q <= 0:
		db.session.delete(item)
	else:
		item.quantity = q

	db.session.commit()
	return True

