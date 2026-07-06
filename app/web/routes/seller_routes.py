"""Seller-facing routes (M10 seller application; M9 sales/shipments).

FR-04 / SFR-04: a logged-in buyer applies to become a verified seller.
The application page shows only the requester's own application — no
route ever exposes another user's application (confidentiality is also
enforced service-side by querying per-user).
"""
from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.security.rbac import login_required, role_required
from app.services import seller_service, shipment_service
from app.services.auth_service import get_current_user

seller_bp = Blueprint("seller", __name__)


@seller_bp.route("/seller/apply", methods=("GET", "POST"))
@login_required
def apply():
    """Apply to become a verified seller (FR-04)."""
    current_user = get_current_user()

    if request.method == "POST":
        application, error = seller_service.apply_to_become_seller(
            current_user, request.form.get("reason", "")
        )
        if error:
            flash(error, "danger")
        else:
            flash(
                "Application submitted — an administrator will review it shortly.",
                "success",
            )
        return redirect(url_for("seller.apply"))

    application = seller_service.get_latest_application_for_user(current_user)
    return render_template(
        "seller/apply.html",
        application=application,
        is_seller=current_user.role.value == "seller",
    )


@seller_bp.route("/seller/sales")
@role_required("seller")
def sales():
    """Orders on the seller's own listings (FR-10 / M9).

    The service scopes the query to the seller's listings, so no other
    seller's orders can appear here (FSR-09/SFR-10).
    """
    rows = shipment_service.get_sales_for_seller(get_current_user())
    return render_template("seller/sales.html", rows=rows)
