import os
import re
from pathlib import Path

from flask import (
	Blueprint,
	abort,
	current_app,
	flash,
	redirect,
	render_template,
	request,
	send_file,
	session,
	url_for,
)

from app.models.enums import ListingCondition, UserRole
from app.models.uploaded_file import UploadedFile
from app.security.ownership import assert_owner
from app.security.rbac import login_required, role_required
from app.services import admin_service
from app.services.auth_service import get_current_user
from app.services.listing_service import (
	create_listing,
	get_listing_by_id,
	get_public_listings_page,
	update_listing,
)

listing_bp = Blueprint("listing", __name__, template_folder="../templates")

# Stored filenames are always uuid4().hex + allow-listed image extension —
# anything else (traversal attempts included) can be rejected outright.
_STORED_NAME_RE = re.compile(r"^[0-9a-f]{32}\.(png|jpg|jpeg|webp)$")

_CONDITION_VALUES = {c.value for c in ListingCondition}

_MAX_TITLE = 200
_MAX_DESCRIPTION = 5000
_MAX_CATEGORY = 50
_MAX_BRAND = 100
_MAX_PRICE = 1_000_000


@listing_bp.route("/listings")
def index():
	"""Public listing index with search + filters (FR-05/FR-06).

	Every parameter is validated/coerced server-side and applied through the
	ORM only — hostile input is data, never SQL (SFR-06 / SDR-03).
	"""
	q = request.args.get("q", "", type=str).strip()[:200]
	category = request.args.get("category", "", type=str).strip()[:_MAX_CATEGORY]
	brand = request.args.get("brand", "", type=str).strip()[:_MAX_BRAND]
	condition = request.args.get("condition", "", type=str)
	if condition not in _CONDITION_VALUES:
		condition = None
	min_price = request.args.get("min_price", None, type=float)
	max_price = request.args.get("max_price", None, type=float)
	page = request.args.get("page", 1, type=int)

	result = get_public_listings_page(
		q=q or None,
		category=category or None,
		brand=brand or None,
		condition=condition,
		min_price=min_price,
		max_price=max_price,
		page=page,
	)

	from app.services.review_service import get_rating_summaries

	ratings = get_rating_summaries([l["id"] for l in result["items"]])

	# Filter args echoed into pagination links (None/empty dropped so URLs
	# stay clean); every value was validated/coerced above.
	filter_args = {
		key: value
		for key, value in {
			"q": q, "category": category, "brand": brand,
			"condition": condition, "min_price": min_price, "max_price": max_price,
		}.items()
		if value not in (None, "")
	}
	return render_template(
		"listings/index.html",
		listings=result["items"],
		pagination=result,
		ratings=ratings,
		filter_args=filter_args,
		filters={
			"q": q, "category": category, "brand": brand,
			"condition": condition or "", "min_price": min_price, "max_price": max_price,
		},
		conditions=sorted(_CONDITION_VALUES),
	)


@listing_bp.route("/listings/<int:listing_id>")
def detail(listing_id):
	"""Listing detail page (FR-05): photos, seller info, specifications.

	Unapproved/rejected listings are public-invisible (404) but stay visible
	to their owner and to admins for moderation (SFR-05).
	"""
	listing = get_listing_by_id(listing_id)
	if not listing:
		abort(404)

	viewer = get_current_user()
	is_owner = viewer is not None and viewer.id == listing["seller_id"]
	is_admin = viewer is not None and viewer.role.value == UserRole.ADMIN.value
	if listing["approval_status"] != "approved" and not (is_owner or is_admin):
		abort(404)

	from app.services.review_service import get_rating_summaries, get_reviews_for_listing

	images = UploadedFile.query.filter_by(listing_id=listing_id).all()
	reviews = get_reviews_for_listing(listing_id)
	rating = get_rating_summaries([listing_id]).get(listing_id)
	return render_template(
		"listings/detail.html",
		listing=listing, images=images, reviews=reviews, rating=rating,
	)


@listing_bp.route("/listings/<int:listing_id>/report", methods=["POST"])
@login_required
def report(listing_id):
	"""Buyer flags a listing as suspicious for admin review (FR-14)."""
	reason = request.form.get("reason", "")
	if admin_service.report_listing(get_current_user(), listing_id, reason) is None:
		abort(404)
	flash("Thank you — this listing has been reported for review.", "info")
	return redirect(url_for("listing.detail", listing_id=listing_id))


@listing_bp.route("/listings/media/<filename>")
def media(filename):
	"""Serve an uploaded listing image safely (SDR-04: no traversal, no
	user-controlled paths — only server-generated names ever resolve)."""
	if not _STORED_NAME_RE.fullmatch(filename):
		abort(404)

	upload_dir = current_app.config.get("UPLOAD_DIR") or os.environ.get("UPLOAD_DIR", "uploads")
	dest_root = (Path(current_app.instance_path) / upload_dir).resolve()
	target = (dest_root / filename).resolve()
	if not str(target).startswith(str(dest_root)) or not target.is_file():
		abort(404)
	return send_file(str(target))


def _validated_listing_fields(form):
	"""Server-side validation for create/edit (SDR-01). Returns (fields, errors)."""
	errors = []
	title = form.get("title", "").strip()
	description = form.get("description", "").strip()
	category = form.get("category", "").strip()
	brand = form.get("brand", "").strip()
	condition = form.get("condition", "").strip()
	price_raw = form.get("price", "0").strip()

	if not title or len(title) > _MAX_TITLE:
		errors.append("Title is required (max 200 characters).")
	if not description or len(description) > _MAX_DESCRIPTION:
		errors.append("Description is required (max 5000 characters).")
	if category and len(category) > _MAX_CATEGORY:
		errors.append("Category is too long.")
	if brand and len(brand) > _MAX_BRAND:
		errors.append("Brand is too long.")
	if condition and condition not in _CONDITION_VALUES:
		errors.append("Invalid condition.")

	try:
		price = float(price_raw)
		if not (0 < price <= _MAX_PRICE):
			errors.append("Price must be between 0 and 1,000,000.")
	except ValueError:
		price = None
		errors.append("Invalid price.")

	fields = {
		"title": title,
		"description": description,
		"price": price,
		"category": category or None,
		"brand": brand or None,
		"condition": ListingCondition(condition) if condition in _CONDITION_VALUES else None,
	}
	return fields, errors


@listing_bp.route("/seller/listings/create", methods=("GET", "POST"))
@role_required("seller")
def create():
	if request.method == "POST":
		fields, errors = _validated_listing_fields(request.form)
		if errors:
			for message in errors:
				flash(message, "danger")
			return render_template("listings/form.html", listing=None, conditions=sorted(_CONDITION_VALUES))

		seller_id = session.get("user_id")
		created = create_listing(
			seller_id,
			fields["title"],
			fields["description"],
			fields["price"],
			category=fields["category"],
			brand=fields["brand"],
			condition=fields["condition"],
		)
		if not created:
			flash("Unable to create listing.", "danger")
			return render_template("listings/form.html", listing=None, conditions=sorted(_CONDITION_VALUES))

		# If an image was uploaded, validate + save it (extension, size,
		# magic bytes; stored under a server-generated name).
		image = request.files.get("image")
		if image:
			from app.services.upload_service import save_upload

			ok, meta = save_upload(image, listing_id=created.get("id"))
			if not ok:
				flash("Listing created but image upload failed: " + "; ".join(meta), "warning")

		flash("Listing created. It will appear publicly once approved by an administrator.", "success")
		return redirect(url_for("listing.detail", listing_id=created["id"]))

	return render_template("listings/form.html", listing=None, conditions=sorted(_CONDITION_VALUES))


@listing_bp.route("/seller/listings/<int:listing_id>/edit", methods=("GET", "POST"))
@role_required("seller")
def edit(listing_id):
	listing = get_listing_by_id(listing_id)
	if not listing:
		abort(404)

	# Ownership check: only the seller who owns the listing may edit (403 on IDOR).
	assert_owner(listing, session.get("user_id"), owner_attr="seller_id")

	if request.method == "POST":
		fields, errors = _validated_listing_fields(request.form)
		if errors:
			for message in errors:
				flash(message, "danger")
			return render_template("listings/form.html", listing=listing, conditions=sorted(_CONDITION_VALUES))

		updates = {k: v for k, v in fields.items() if v is not None}
		updated = update_listing(listing_id, session.get("user_id"), **updates)
		if not updated:
			flash("Unable to update listing.", "danger")
			return render_template("listings/form.html", listing=listing, conditions=sorted(_CONDITION_VALUES))

		image = request.files.get("image")
		if image:
			from app.services.upload_service import save_upload

			ok, meta = save_upload(image, listing_id=listing_id)
			if not ok:
				flash("Listing updated but image upload failed: " + "; ".join(meta), "warning")

		flash("Listing updated.", "success")
		return redirect(url_for("listing.detail", listing_id=listing_id))

	return render_template("listings/form.html", listing=listing, conditions=sorted(_CONDITION_VALUES))
