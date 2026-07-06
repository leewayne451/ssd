"""Shipment routes (M9 — FR-10 / SFR-10).

A seller records the shipment of an order placed on one of their OWN
listings: tracking reference + awaiting_shipment -> shipped through the
audited workflow state machine. Buyers never update shipments; they read
tracking from their order page (order_routes).
"""
from flask import Blueprint, flash, redirect, request, url_for

from app.security.rbac import role_required
from app.services import shipment_service
from app.services.auth_service import get_current_user

shipment_bp = Blueprint("shipment", __name__)


@shipment_bp.route("/orders/<int:order_id>/shipment", methods=["POST"])
@role_required("seller")
def mark_shipped(order_id):
    try:
        shipment_service.mark_shipped(
            get_current_user(), order_id, request.form.get("tracking_number", "")
        )
        flash("Order marked as shipped.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    except PermissionError:
        flash("You can only update shipments for your own listings.", "danger")
    return redirect(url_for("seller.sales"))
