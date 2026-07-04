from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
from flask_login import login_required, current_user

from app.extensions import db
from app.models.cart import Cart
from app.services import cart_service

cart_bp = Blueprint("cart", __name__)


@cart_bp.route("/cart", methods=["GET"])
@login_required
def view_cart():
    """View the current user's cart."""
    cart = cart_service.get_cart_for_user(current_user)
    total = cart_service.get_cart_total(current_user)
    return render_template("cart/view.html", cart=cart, total=total)


@cart_bp.route("/cart/add", methods=["POST"])
@login_required
def add_to_cart():
    """Add an item to the cart."""
    listing_id = request.form.get("listing_id", type=int)
    quantity = request.form.get("quantity", default=1, type=int)

    if not listing_id:
        return jsonify({"error": "Missing listing_id"}), 400

    try:
        cart_service.add_item(current_user, listing_id, quantity)
        return redirect(request.referrer or url_for("cart.view_cart"))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@cart_bp.route("/cart/remove", methods=["POST"])
@login_required
def remove_from_cart():
    """Remove an item from the cart."""
    listing_id = request.form.get("listing_id", type=int)

    if not listing_id:
        return jsonify({"error": "Missing listing_id"}), 400

    removed = cart_service.remove_item(current_user, listing_id)
    if not removed:
        return jsonify({"error": "Item not found in cart"}), 404

    return redirect(url_for("cart.view_cart"))


@cart_bp.route("/cart/update", methods=["POST"])
@login_required
def update_cart_item():
    """Update the quantity of an item in the cart."""
    listing_id = request.form.get("listing_id", type=int)
    quantity = request.form.get("quantity", type=int)

    if not listing_id or quantity is None:
        return jsonify({"error": "Missing listing_id or quantity"}), 400

    try:
        updated = cart_service.update_item_quantity(current_user, listing_id, quantity)
        if not updated:
            return jsonify({"error": "Item not found in cart"}), 404
        return redirect(url_for("cart.view_cart"))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@cart_bp.route("/cart/clear", methods=["POST"])
@login_required
def clear_cart():
    """Clear all items from the cart."""
    cart_service.clear_cart(current_user)
    return redirect(url_for("cart.view_cart"))
