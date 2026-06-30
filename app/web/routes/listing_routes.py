from flask import Blueprint, render_template, abort, request, redirect, url_for, session, flash, send_file, current_app
import os
from app.services.listing_service import (
	get_public_listings,
	get_listing_by_id,
	create_listing,
	update_listing,
)
from app.security.rbac import role_required
from app.security.ownership import assert_owner
from pathlib import Path


listing_bp = Blueprint("listing", __name__, template_folder="../templates")


@listing_bp.route("/listings")
def index():
	"""Public listing index (buyer read path)."""
	listings = get_public_listings()
	return render_template("listings/index.html", listings=listings)


@listing_bp.route("/listings/<int:listing_id>")
def detail(listing_id):
	"""Listing detail view for buyers."""
	target = dest_root.joinpath(filename).resolve()
	try:
		if not str(target).startswith(str(dest_root.resolve())):
			abort(404)
		return send_file(str(target))
	except FileNotFoundError:
		abort(404)



@listing_bp.route("/seller/listings/create", methods=("GET", "POST"))
@role_required("seller")
def create():
	if request.method == "POST":
		title = request.form.get("title", "").strip()
		description = request.form.get("description", "").strip()
		price = request.form.get("price", "0").strip()
		image = request.files.get("image")

		if not title or not description:
			flash("Title and description are required.", "danger")
			return render_template("listings/form.html", listing=None)

		try:
			price_val = float(price)
		except ValueError:
			flash("Invalid price.", "danger")
			return render_template("listings/form.html", listing=None)

		seller_id = session.get("user_id")
		created = create_listing(seller_id, title, description, price_val)
		if not created:
			flash("Unable to create listing.", "danger")
			return render_template("listings/form.html", listing=None)

		# If an image was uploaded, save it and associate with the listing
		if image:
			from app.services.upload_service import save_upload

			ok, meta = save_upload(image, listing_id=created.get("id"))
			if not ok:
				# Non-blocking: show warning but proceed
				flash("Listing created but image upload failed: " + "; ".join(meta), "warning")

		flash("Listing created.", "success")
		return redirect(url_for("listing.detail", listing_id=created["id"]))

	return render_template("listings/form.html", listing=None)


@listing_bp.route("/seller/listings/<int:listing_id>/edit", methods=("GET", "POST"))
@role_required("seller")
def edit(listing_id):
	listing = get_listing_by_id(listing_id)
	if not listing:
		abort(404)

	# Ownership check: only the seller who owns the listing may edit (403 on IDOR).
	assert_owner(listing, session.get("user_id"), owner_attr="seller_id")

	if request.method == "POST":
		title = request.form.get("title", "").strip()
		description = request.form.get("description", "").strip()
		price = request.form.get("price", "0").strip()
		image = request.files.get("image")

		if not title or not description:
			flash("Title and description are required.", "danger")
			return render_template("listings/form.html", listing=listing)


		try:
			price_val = float(price)
		except ValueError:
			flash("Invalid price.", "danger")
			return render_template("listings/form.html", listing=listing)

		updated = update_listing(listing_id, session.get("user_id"), title=title, description=description, price=price_val)
		if not updated:
			flash("Unable to update listing.", "danger")
			return render_template("listings/form.html", listing=listing)

		if image:
			from app.services.upload_service import save_upload

			ok, meta = save_upload(image, listing_id=listing_id)
			if not ok:
				flash("Listing updated but image upload failed: " + "; ".join(meta), "warning")

		flash("Listing updated.", "success")
		return redirect(url_for("listing.detail", listing_id=listing_id))

	return render_template("listings/form.html", listing=listing)
