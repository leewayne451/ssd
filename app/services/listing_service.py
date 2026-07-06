"""listing_service — listing catalogue logic (FR-05..07).

Public queries are approval-filtered (SFR-05) and built exclusively through
the ORM with bound parameters (SDR-03). Mutations enforce the seller-owns
rule and an explicit field allow-list against mass assignment.
"""

from typing import List, Optional

from app.extensions import db
from app.models.enums import ApprovalStatus, ListingCondition
from app.models.product_listing import ProductListing


def _serialize_listing(obj) -> dict:
	return {
		"id": obj.id,
		"seller_id": getattr(obj, "seller_id", None),
		"title": obj.title,
		"description": obj.description,
		"category": getattr(obj, "category", None),
		"brand": getattr(obj, "brand", None),
		"condition": getattr(getattr(obj, "condition", None), "value", getattr(obj, "condition", None)),
		"price": float(obj.price) if getattr(obj, "price", None) is not None else None,
		"approval_status": getattr(getattr(obj, "approval_status", None), "value", getattr(obj, "approval_status", None)),
		"workflow_status": getattr(getattr(obj, "workflow_status", None), "value", getattr(obj, "workflow_status", None)),
		"is_active": getattr(obj, "is_active", True),
		"created_at": getattr(obj, "created_at", None),
	}


def _public_query(
	q: Optional[str] = None,
	category: Optional[str] = None,
	brand: Optional[str] = None,
	condition: Optional[str] = None,
	min_price: Optional[float] = None,
	max_price: Optional[float] = None,
):
	"""Shared filter builder for the public index (FR-05/06).

	Pending/rejected listings never appear here — D1: second-hand items stay
	hidden until admin approval (SFR-05 / TRACE-003). All filtering happens
	through the ORM with bound parameters (SDR-03); no user input is ever
	interpolated into SQL.
	"""
	query = ProductListing.query.filter(
		ProductListing.is_active.is_(True),
		ProductListing.approval_status == ApprovalStatus.APPROVED,
	)

	if q:
		like = f"%{q}%"
		query = query.filter(
			db.or_(ProductListing.title.ilike(like), ProductListing.description.ilike(like))
		)
	if category:
		query = query.filter(ProductListing.category.ilike(category))
	if brand:
		query = query.filter(ProductListing.brand.ilike(brand))
	if condition in {c.value for c in ListingCondition}:
		query = query.filter(ProductListing.condition == ListingCondition(condition))
	if min_price is not None:
		query = query.filter(ProductListing.price >= min_price)
	if max_price is not None:
		query = query.filter(ProductListing.price <= max_price)

	return query.order_by(ProductListing.created_at.desc(), ProductListing.id.desc())


def get_public_listings(
	q: Optional[str] = None,
	category: Optional[str] = None,
	brand: Optional[str] = None,
	condition: Optional[str] = None,
	min_price: Optional[float] = None,
	max_price: Optional[float] = None,
) -> List[dict]:
	"""Unpaginated view of the public index (kept for service-level callers
	and tests; the HTTP index uses get_public_listings_page)."""
	results = _public_query(q, category, brand, condition, min_price, max_price).limit(100).all()
	return [_serialize_listing(r) for r in results]


def get_public_listings_page(
	q: Optional[str] = None,
	category: Optional[str] = None,
	brand: Optional[str] = None,
	condition: Optional[str] = None,
	min_price: Optional[float] = None,
	max_price: Optional[float] = None,
	page: int = 1,
	per_page: int = 12,
) -> dict:
	"""Paginated public index (NFR-10: stays usable at 1,000+ listings).

	`page` is clamped server-side; out-of-range pages return empty items
	rather than erroring (error_out=False)."""
	try:
		page = max(1, int(page or 1))
	except (TypeError, ValueError):
		page = 1
	pagination = _public_query(
		q, category, brand, condition, min_price, max_price
	).paginate(page=page, per_page=per_page, error_out=False)
	return {
		"items": [_serialize_listing(r) for r in pagination.items],
		"page": pagination.page,
		"pages": pagination.pages,
		"total": pagination.total,
		"has_prev": pagination.has_prev,
		"has_next": pagination.has_next,
		"prev_num": pagination.prev_num,
		"next_num": pagination.next_num,
	}


def get_listing_by_id(listing_id: int) -> Optional[dict]:
	"""Load one active listing (any approval state — the ROUTE decides
	visibility: owners/admins may see their unapproved listings, the public
	may not)."""
	obj = db.session.get(ProductListing, listing_id)
	if not obj or not getattr(obj, "is_active", True):
		return None
	return _serialize_listing(obj)


def create_listing(seller_id: int, title: str, description: str, price: float, **kwargs) -> Optional[dict]:
	"""Create a new ProductListing and return serialized dict.

	New listings always start PENDING (D1: hidden until admin approval) —
	a seller cannot self-approve via mass assignment.
	"""
	defaults = {
		"category": kwargs.get("category") or "uncategorized",
		"brand": kwargs.get("brand") or "unknown",
		"condition": kwargs.get("condition") or ListingCondition.PRE_OWNED,
	}

	obj = ProductListing(
		seller_id=seller_id,
		title=title,
		description=description,
		price=price,
		category=defaults["category"],
		brand=defaults["brand"],
		condition=defaults["condition"],
		approval_status=ApprovalStatus.PENDING,
	)
	db.session.add(obj)
	db.session.commit()
	return _serialize_listing(obj)


_EDITABLE_FIELDS = {"title", "description", "price", "category", "brand", "condition"}


def update_listing(listing_id: int, seller_id: int, **updates) -> Optional[dict]:
	"""Apply allow-listed edits to the seller's OWN listing; returns the serialized listing, or None when missing or not owned.
	"""
	obj = db.session.get(ProductListing, listing_id)
	if not obj or obj.seller_id != seller_id:
		return None

	# Explicit allow-list: approval_status / is_active / seller_id can never
	# be mass-assigned through an edit request.
	for k, v in updates.items():
		if k in _EDITABLE_FIELDS:
			setattr(obj, k, v)

	db.session.add(obj)
	db.session.commit()
	return _serialize_listing(obj)
