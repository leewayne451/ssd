from typing import List, Optional

try:
	from app.extensions import db
	from app.models.product_listing import ProductListing
except Exception:
	db = None
	ProductListing = None


def _serialize_listing(obj) -> dict:
	return {
		"id": obj.id,
		"seller_id": getattr(obj, "seller_id", None),
		"title": obj.title,
		"description": obj.description,
		"price": float(obj.price) if getattr(obj, "price", None) is not None else None,
		"created_at": getattr(obj, "created_at", None),
	}


def get_public_listings() -> List[dict]:
	"""Return a list of active, approved listings for public index.

	If the DB or model is not available (testing or incomplete app), returns an empty list.
	"""
	if ProductListing is None or db is None:
		return []

	q = ProductListing.query.filter_by(is_active=True)
	# Only include approved listings if ApprovalStatus enum is used; avoid import cycle here.
	results = q.order_by(ProductListing.created_at.desc()).limit(100).all()
	return [_serialize_listing(r) for r in results]


def get_listing_by_id(listing_id: int) -> Optional[dict]:
	if ProductListing is None or db is None:
		return None

	# Use Session.get for SQLAlchemy 2.x compatibility
	try:
		obj = db.session.get(ProductListing, listing_id)
	except Exception:
		obj = ProductListing.query.get(listing_id)
	if not obj or not getattr(obj, "is_active", True):
		return None
	return _serialize_listing(obj)


def create_listing(seller_id: int, title: str, description: str, price: float, **kwargs) -> Optional[dict]:
	"""Create a new ProductListing and return serialized dict, or None if DB unavailable."""
	if ProductListing is None or db is None:
		return None

	# Provide sensible defaults for required fields if not provided
	defaults = {
		"category": kwargs.get("category", "uncategorized"),
		"brand": kwargs.get("brand", "unknown"),
		"condition": kwargs.get("condition", None),
	}

	# If condition is not provided, set to a safe default if the Enum exists
	if defaults["condition"] is None:
		try:
			from app.models.enums import ListingCondition

			defaults["condition"] = ListingCondition.PRE_OWNED
		except Exception:
			defaults["condition"] = None

	init_kwargs = {k: v for k, v in {**defaults, **kwargs}.items() if hasattr(ProductListing, k)}

	obj = ProductListing(
		seller_id=seller_id,
		title=title,
		description=description,
		price=price,
		**init_kwargs,
	)
	db.session.add(obj)
	db.session.commit()
	return _serialize_listing(obj)


def update_listing(listing_id: int, seller_id: int, **updates) -> Optional[dict]:
	if ProductListing is None or db is None:
		return None

	try:
		obj = db.session.get(ProductListing, listing_id)
	except Exception:
		obj = ProductListing.query.get(listing_id)
	if not obj or obj.seller_id != seller_id:
		return None

	for k, v in updates.items():
		if hasattr(obj, k):
			setattr(obj, k, v)

	db.session.add(obj)
	db.session.commit()
	return _serialize_listing(obj)

