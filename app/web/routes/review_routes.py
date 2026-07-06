"""Review routes (M8 — FR-16 / SFR-16).

One endpoint: the buyer of a completed (sold) order submits a rating and
comment from their order-detail page. Eligibility (buyer-owns-order,
workflow sold, one review per order) is enforced in review_service —
this route never trusts the form to decide who may review what.
Reviews are displayed on the public listing detail page (autoescaped).
"""
from flask import Blueprint, flash, redirect, request, url_for

from app.security.rbac import login_required
from app.services import review_service
from app.services.auth_service import get_current_user

review_bp = Blueprint("review", __name__)


@review_bp.route("/orders/<int:order_id>/review", methods=["POST"])
@login_required
def submit(order_id):
    review, error = review_service.create_review(
        get_current_user(),
        order_id,
        request.form.get("rating", ""),
        request.form.get("comment", ""),
    )
    if error:
        flash(error, "danger")
    else:
        flash("Thank you — your review has been published.", "success")
    return redirect(url_for("order.order_detail", order_id=order_id))
