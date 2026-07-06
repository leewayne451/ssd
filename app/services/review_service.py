# review_service — purchase-based reviews (FR-16 / SFR-16, D1 UC-06).
#
# A review may exist only for a COMPLETED purchase: the order must belong to
# the reviewer and have finished the workflow (sold). One review per order
# (DB-unique), rating clamped server-side to 1–5, comment length-capped.
# Review text is stored raw and escaped on output by Jinja autoescape
# (SDR-02) — the classic stored-XSS surface, covered by template tests.
import logging

from app.extensions import db
from app.models.enums import WorkflowStatus
from app.models.order import Order
from app.models.review import Review
from app.services.audit_service import record as audit_record

logger = logging.getLogger(__name__)

MAX_COMMENT_LENGTH = 2000
RATING_MIN, RATING_MAX = 1, 5


def create_review(user, order_id: int, rating, comment: str = "") -> tuple[Review | None, str | None]:
    """
    Create a review for `order_id` by `user`. Returns (review, error).

    Eligibility is decided entirely server-side (SFR-16):
      * the order exists and `user` is its buyer — nobody can review another
        buyer's purchase;
      * the order's workflow is `sold` — the purchase completed the full
        commit → authenticate → checkout flow;
      * no review exists yet for this order.
    """
    if user is None:
        return None, "You must be logged in to review."

    order = db.session.get(Order, order_id)
    if order is None or order.buyer_id != user.id:
        # Same answer for "missing" and "not yours": no resource probing.
        return None, "Order not found."

    workflow = getattr(order.workflow_status, "value", order.workflow_status)
    if workflow != WorkflowStatus.SOLD.value:
        return None, "You can only review completed purchases."

    if Review.query.filter_by(order_id=order.id).first() is not None:
        return None, "You have already reviewed this purchase."

    try:
        rating = int(rating)
    except (TypeError, ValueError):
        return None, "Rating must be a number from 1 to 5."
    if not (RATING_MIN <= rating <= RATING_MAX):
        return None, "Rating must be between 1 and 5."

    comment = (comment or "").strip()
    if len(comment) > MAX_COMMENT_LENGTH:
        return None, f"Comment is too long (max {MAX_COMMENT_LENGTH} characters)."

    review = Review(
        order_id=order.id,
        buyer_id=user.id,
        listing_id=order.listing_id,
        rating=rating,
        comment=comment or None,
    )
    db.session.add(review)
    db.session.commit()

    audit_record(user, "review_created", "review", review.id,
                 {"order_id": order.id, "listing_id": order.listing_id})
    return review, None


def get_reviews_for_listing(listing_id: int) -> list[Review]:
    """Public: reviews shown on the listing detail page, newest first."""
    return (
        Review.query.filter_by(listing_id=listing_id)
        .order_by(Review.created_at.desc(), Review.id.desc())
        .all()
    )


def get_review_for_order(order_id: int) -> Review | None:
    return Review.query.filter_by(order_id=order_id).first()


def can_review(user, order) -> bool:
    """True when the order-detail page should offer the review form."""
    if user is None or order is None or order.buyer_id != user.id:
        return False
    workflow = getattr(order.workflow_status, "value", order.workflow_status)
    if workflow != WorkflowStatus.SOLD.value:
        return False
    return get_review_for_order(order.id) is None
