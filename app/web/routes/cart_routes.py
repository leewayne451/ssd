from flask import Blueprint, jsonify, request, abort

from app.services.auth_service import get_current_user
from app.services import cart_service
from app.security.ownership import assert_owner

cart_bp = Blueprint("cart", __name__, url_prefix="/cart")


@cart_bp.route("/", methods=["GET"])
def view_cart():
	current_user = get_current_user()
	if current_user is None:
		abort(401)

	cart = cart_service.get_cart_for_user(current_user)
	if not cart:
		return jsonify({"items": []})

	# Owner check (defence-in-depth)
	assert_owner(cart, current_user, owner_attr="buyer_id")

	items = []
	from app.models.product_listing import ProductListing

	for it in cart.items:
		listing = ProductListing.query.get(it.listing_id)
		items.append({
			"listing_id": it.listing_id,
			"title": getattr(listing, "title", None),
			"price": float(getattr(listing, "price", None)) if listing is not None else None,
			"quantity": int(getattr(it, "quantity", 1)),
			"added_at": it.added_at.isoformat() if getattr(it, "added_at", None) else None,
		})

	return jsonify({"items": items})


@cart_bp.route("/add", methods=["POST"])
def add_to_cart():
	current_user = get_current_user()
	if current_user is None:
		abort(401)

	json_data = request.get_json(silent=True) or {}
	listing_id = request.form.get("listing_id") or json_data.get("listing_id")
	quantity = request.form.get("quantity") or json_data.get("quantity")

	if listing_id is None:
		return jsonify({"error": "listing_id required"}), 400

	try:
		q = int(quantity) if quantity is not None else 1
		item = cart_service.add_item(current_user, int(listing_id), q)
	except ValueError as exc:
		return jsonify({"error": str(exc)}), 400

	return jsonify({"id": item.id, "listing_id": item.listing_id}), 201


@cart_bp.route("/remove", methods=["POST"])
def remove_from_cart():
	current_user = get_current_user()
	if current_user is None:
		abort(401)

	json_data = request.get_json(silent=True) or {}
	listing_id = request.form.get("listing_id") or json_data.get("listing_id")
	if listing_id is None:
		return jsonify({"error": "listing_id required"}), 400

	removed = cart_service.remove_item(current_user, int(listing_id))
	if not removed:
		return jsonify({"error": "not found"}), 404
	return jsonify({"removed": True})


@cart_bp.route("/clear", methods=["POST"])
def clear_cart():
	current_user = get_current_user()
	if current_user is None:
		abort(401)
	cart_service.clear_cart(current_user)
	return jsonify({"cleared": True})


@cart_bp.route("/update", methods=["POST"])
def update_cart_item():
	current_user = get_current_user()
	if current_user is None:
		abort(401)

	json_data = request.get_json(silent=True) or {}
	listing_id = request.form.get("listing_id") or json_data.get("listing_id")
	quantity = request.form.get("quantity") or json_data.get("quantity")

	if listing_id is None or quantity is None:
		return jsonify({"error": "listing_id and quantity required"}), 400

	try:
		ok = cart_service.update_item_quantity(current_user, int(listing_id), int(quantity))
	except ValueError as exc:
		return jsonify({"error": str(exc)}), 400

	if not ok:
		return jsonify({"error": "not found"}), 404
	return jsonify({"updated": True})

