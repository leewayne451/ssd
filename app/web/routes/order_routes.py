from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user

from app.extensions import db
from app.models.order import Order
from app.services import order_service, workflow_service

order_bp = Blueprint("order", __name__)


@order_bp.route("/orders/place", methods=["POST"])
@login_required
def place_orders():
    """Place orders from the current cart."""
    try:
        orders = order_service.place_orders_from_cart(current_user)
        if not orders:
            return jsonify({"error": "Cart is empty"}), 400
        
        # Redirect to order confirmation/list
        return redirect(url_for("order.list_orders"))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@order_bp.route("/orders", methods=["GET"])
@login_required
def list_orders():
    """List all orders for the current user."""
    page = request.args.get("page", 1, type=int)
    per_page = 10
    
    # Only show orders where current_user is the buyer
    orders = (
        Order.query.filter_by(buyer_id=current_user.id)
        .order_by(Order.created_at.desc())
        .paginate(page=page, per_page=per_page)
    )
    
    return render_template("orders/list.html", orders=orders)


@order_bp.route("/orders/<int:order_id>", methods=["GET"])
@login_required
def order_detail(order_id):
    """Get details for a specific order."""
    order = Order.query.get(order_id)
    
    if not order:
        return jsonify({"error": "Order not found"}), 404
    
    # IDOR protection: only allow buyer to view their own order
    if order.buyer_id != current_user.id:
        return jsonify({"error": "Forbidden"}), 403
    
    return render_template("orders/detail.html", order=order)


@order_bp.route("/orders/<int:order_id>/transition", methods=["POST"])
@login_required
def transition_order_status(order_id):
    """Transition an order to a new workflow status."""
    order = Order.query.get(order_id)
    
    if not order:
        return jsonify({"error": "Order not found"}), 404
    
    # Note: RBAC check is done in workflow_service.transition_order()
    # but we can add additional checks here if needed
    
    new_status = request.form.get("new_status")
    if not new_status:
        return jsonify({"error": "Missing new_status"}), 400
    
    try:
        workflow_service.transition_order(order, new_status, current_user)
        return redirect(url_for("order.order_detail", order_id=order_id))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except Exception as e:
        return jsonify({"error": "Failed to transition order"}), 500
