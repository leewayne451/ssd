from flask import Blueprint, render_template, request, jsonify, redirect, url_for

from app.extensions import db
from app.models.enums import WorkflowStatus
from app.models.order import Order
from app.security.rbac import login_required
from app.security.ownership import require_order_buyer, user_is_order_buyer
from app.services import checkout_service, order_service, workflow_service
from app.services.auth_service import get_current_user

_VALID_WORKFLOW_VALUES = {status.value for status in WorkflowStatus}

order_bp = Blueprint("order", __name__)


@order_bp.route("/orders/place", methods=["POST"])
@login_required
def place_orders():
    """Place orders from the current cart."""
    current_user = get_current_user()
    try:
        orders = order_service.place_orders_from_cart(current_user)
        if not orders:
            return jsonify({"error": "Cart is empty"}), 400

        # Redirect to order confirmation/list
        return redirect(url_for("order.list_orders"))
    except Exception:
        return jsonify({"error": "Failed to place orders"}), 500


@order_bp.route("/orders", methods=["GET"])
@login_required
def list_orders():
    """List all orders for the current user."""
    current_user = get_current_user()
    page = request.args.get("page", 1, type=int)
    per_page = 10

    # Only show orders where the current user is the buyer
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
    current_user = get_current_user()
    order = db.session.get(Order, order_id)

    # IDOR protection: only the buyer may view their own order (404/403 inside)
    require_order_buyer(order, current_user)

    return render_template("orders/detail.html", order=order)


@order_bp.route("/orders/<int:order_id>/transition", methods=["POST"])
@login_required
def transition_order_status(order_id):
    """
    Transition an order to a new workflow status (seller/admin actions).

    Hardened per SURFACE-001: the submitted status is validated against the
    WorkflowStatus enum before it reaches the service; role + ownership +
    state-machine checks (and audit of accepted AND rejected attempts) happen
    inside workflow_service.transition_order.
    """
    current_user = get_current_user()
    order = db.session.get(Order, order_id)

    if not order:
        return jsonify({"error": "Order not found"}), 404

    new_status = request.form.get("new_status", "")
    if new_status not in _VALID_WORKFLOW_VALUES:
        return jsonify({"error": "Invalid new_status"}), 400

    try:
        workflow_service.transition_order(order, new_status, current_user)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except Exception:
        return jsonify({"error": "Failed to transition order"}), 500

    # Buyers land on their order; sellers/admins have no access to the
    # buyer-private detail page.
    if user_is_order_buyer(order, current_user):
        return redirect(url_for("order.order_detail", order_id=order_id))
    return redirect(url_for("public.index"))


@order_bp.route("/orders/<int:order_id>/checkout", methods=["POST"])
@login_required
def checkout(order_id):
    """
    Simulated checkout (FR-11). The server decides every payment value —
    any client-submitted payment_status/price fields are ignored entirely.
    """
    current_user = get_current_user()
    order = db.session.get(Order, order_id)

    if not order:
        return jsonify({"error": "Order not found"}), 404

    try:
        checkout_service.checkout_order(order, current_user)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except PermissionError:
        return jsonify({"error": "Forbidden"}), 403

    return redirect(url_for("order.order_detail", order_id=order_id))
