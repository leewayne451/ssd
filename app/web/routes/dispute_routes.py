"""Dispute routes (M11 — FR-17 / SFR-17).

Buyers raise a dispute from their own order page and see their own disputes
at /disputes. Ownership is enforced in dispute_service (order must belong to
the requester); admins handle disputes from the gated /admin/disputes queue.
"""
from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.security.rbac import login_required
from app.services import dispute_service
from app.services.auth_service import get_current_user

dispute_bp = Blueprint("dispute", __name__)


@dispute_bp.route("/orders/<int:order_id>/dispute", methods=["POST"])
@login_required
def raise_dispute(order_id):
    dispute, error = dispute_service.raise_dispute(
        get_current_user(), order_id, request.form.get("reason", "")
    )
    if error:
        flash(error, "danger")
        return redirect(url_for("order.order_detail", order_id=order_id))
    flash("Dispute submitted — an administrator will review it.", "success")
    return redirect(url_for("dispute.my_disputes"))


@dispute_bp.route("/disputes")
@login_required
def my_disputes():
    disputes = dispute_service.get_disputes_for_user(get_current_user())
    return render_template("disputes/list.html", disputes=disputes)
