"""M8 — purchase-based reviews (FR-16 / SFR-16, D1 UC-06).

Reviews exist only for completed (sold) purchases, only from the order's
buyer, one per order. Review comments are hostile user content: the listing
page must render them autoescaped (SDR-02 stored-XSS evidence).
"""

import time

from app.extensions import db
from app.models.audit_log import AuditLog
from app.models.enums import (
    ApprovalStatus,
    ListingCondition,
    UserRole,
    WorkflowStatus,
)
from app.models.order import Order
from app.models.product_listing import ProductListing
from app.models.review import Review
from app.models.user import User


def _listing(status=ApprovalStatus.APPROVED):
    seller = User(email=f"seller{time.time_ns()}@example.com", password_hash="x",
                  role=UserRole.SELLER, status="active")
    db.session.add(seller)
    db.session.commit()
    listing = ProductListing(
        seller_id=seller.id, title="Reviewed bag", description="d",
        category="bags", brand="B", price=100.0,
        condition=ListingCondition.PRE_OWNED, approval_status=status,
    )
    db.session.add(listing)
    db.session.commit()
    return listing


def _order_for(buyer, listing, workflow=WorkflowStatus.SOLD):
    order = Order(
        buyer_id=buyer.id, listing_id=listing.id,
        committed_price=listing.price, workflow_status=workflow,
    )
    db.session.add(order)
    db.session.commit()
    return order


# ------------------- happy path ---------------------------------------------

def test_buyer_reviews_completed_purchase(client, login_as):
    buyer = login_as("happybuyer@example.com")
    listing = _listing()
    order = _order_for(buyer, listing)

    resp = client.post(
        f"/orders/{order.id}/review",
        data={"rating": "5", "comment": "Authenticated fast, item as described."},
        follow_redirects=True,
    )
    assert resp.status_code == 200

    review = Review.query.filter_by(order_id=order.id).one()
    assert review.rating == 5 and review.buyer_id == buyer.id

    # Audit row for the key action (FSR-11)
    assert AuditLog.query.filter_by(
        action_type="review_created", target_id=review.id
    ).first() is not None

    # Visible on the public listing page
    page = client.get(f"/listings/{listing.id}")
    assert b"Authenticated fast, item as described." in page.data


# ------------------- SFR-16 gating -------------------------------------------

def test_review_blocked_before_purchase_completes(client, login_as):
    buyer = login_as("impatient@example.com")
    order = _order_for(buyer, _listing(), workflow=WorkflowStatus.COMMITTED)

    client.post(f"/orders/{order.id}/review",
                data={"rating": "5", "comment": "too early"},
                follow_redirects=True)
    assert Review.query.filter_by(order_id=order.id).count() == 0


def test_non_buyer_cannot_review_someone_elses_order(client, db_session, login_as):
    real_buyer = User(email="realbuyer@example.com", password_hash="x",
                      role=UserRole.BUYER, status="active")
    db.session.add(real_buyer)
    db.session.commit()
    order = _order_for(real_buyer, _listing())

    login_as("imposter@example.com")
    client.post(f"/orders/{order.id}/review",
                data={"rating": "1", "comment": "sabotage"},
                follow_redirects=True)
    assert Review.query.filter_by(order_id=order.id).count() == 0


def test_one_review_per_order(client, login_as):
    buyer = login_as("repeat@example.com")
    order = _order_for(buyer, _listing())

    for comment in ("first", "second"):
        client.post(f"/orders/{order.id}/review",
                    data={"rating": "4", "comment": comment},
                    follow_redirects=True)

    reviews = Review.query.filter_by(order_id=order.id).all()
    assert len(reviews) == 1 and reviews[0].comment == "first"


def test_rating_validated_server_side(client, login_as):
    buyer = login_as("outofrange@example.com")
    listing = _listing()

    for bad in ("0", "6", "-1", "abc", ""):
        order = _order_for(buyer, listing)
        client.post(f"/orders/{order.id}/review",
                    data={"rating": bad, "comment": "x"},
                    follow_redirects=True)
        assert Review.query.filter_by(order_id=order.id).count() == 0


def test_anonymous_cannot_review(client, db_session):
    assert client.post("/orders/1/review", data={"rating": "5"}).status_code == 401


# ------------------- SDR-02: stored XSS is neutralised -----------------------

def test_review_comment_is_escaped_on_listing_page(client, login_as):
    buyer = login_as("xsstester@example.com")
    listing = _listing()
    order = _order_for(buyer, listing)

    payload = '<script>alert("xss")</script>'
    client.post(f"/orders/{order.id}/review",
                data={"rating": "5", "comment": payload},
                follow_redirects=True)
    assert Review.query.filter_by(order_id=order.id).count() == 1

    page = client.get(f"/listings/{listing.id}")
    assert b"<script>alert(" not in page.data          # raw payload never ships
    assert b"&lt;script&gt;alert(" in page.data        # escaped form does
