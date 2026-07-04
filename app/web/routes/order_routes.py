from flask import Blueprint, jsonify, abort, request

from app.models.enums import UserRole
from app.models.product_listing import ProductListing
from app.services.auth_service import get_current_user
from app.services import order_service
from app.services.workflow_service import transition_order

order_bp = Blueprint("order", __name__, url_prefix="/orders")


@order_bp.route("/place", methods=["POST"])
def place_order():
	current_user = get_current_user()
	if current_user is None:
		abort(401)

	orders = order_service.place_orders_from_cart(current_user)
	ids = [o.id for o in orders]
	return jsonify({"created_order_ids": ids}), 201


@order_bp.route("/<int:order_id>/status", methods=["POST"])
def change_order_status(order_id):
	current_user = get_current_user()
	if current_user is None:
		abort(401)

	json_data = request.get_json(silent=True) or {}
	new_status = request.form.get("new_status") or json_data.get("new_status")
	if not new_status:
		return jsonify({"error": "new_status required"}), 400

	from app.models.order import Order

	order = Order.query.get(order_id)
	if not order:
		abort(404)

	# allow buyer-owned transitions, seller-owned listing transitions, or admin actions
	if current_user.role == UserRole.ADMIN:
		pass
	elif current_user.role == UserRole.SELLER:
		listing = ProductListing.query.get(order.listing_id)
		if not listing or listing.seller_id != current_user.id:
			abort(403)
	elif current_user.role == UserRole.BUYER:
		if order.buyer_id != current_user.id:
			abort(403)
	else:
		abort(403)

	try:
		transition_order(order, new_status, current_user)
	except ValueError as exc:
		return jsonify({"error": str(exc)}), 400
	except PermissionError as exc:
		return jsonify({"error": str(exc)}), 403

	return jsonify({"id": order.id, "new_status": new_status})

