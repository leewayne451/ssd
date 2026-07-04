from flask import Blueprint, jsonify, abort, request

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

	new_status = request.form.get("new_status") or (request.json and request.json.get("new_status"))
	if not new_status:
		return jsonify({"error": "new_status required"}), 400

	from app.models.order import Order

	order = Order.query.get(order_id)
	if not order:
		abort(404)

	# ownership: only buyer who placed the order may change it in this phase
	if order.buyer_id != current_user.id:
		abort(403)

	try:
		transition_order(order, new_status, current_user)
	except ValueError as exc:
		return jsonify({"error": str(exc)}), 400

	return jsonify({"id": order.id, "new_status": new_status})

