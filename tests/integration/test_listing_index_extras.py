"""Listing index pagination (NFR-10) + aggregate ratings (FR-16 display).

UI-audit items 11+12: /listings now paginates (12 per page, filters preserved
in the links, hostile page values neutralised) and shows average ratings
computed in a single grouped query.
"""

import time

from app.extensions import db
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


def _seller():
    seller = User(email=f"s{time.time_ns()}@example.com", password_hash="x",
                  role=UserRole.SELLER, status="active")
    db.session.add(seller)
    db.session.commit()
    return seller


def _approved(seller, title):
    listing = ProductListing(
        seller_id=seller.id, title=title, description="d",
        category="bags", brand="B", price=10.0,
        condition=ListingCondition.PRE_OWNED,
        approval_status=ApprovalStatus.APPROVED,
    )
    db.session.add(listing)
    db.session.commit()
    return listing


def test_index_paginates_at_twelve_per_page(client, db_session):
    seller = _seller()
    for i in range(15):
        _approved(seller, f"PAGED-ITEM-{i:02d}")

    page1 = client.get("/listings")
    assert page1.status_code == 200
    assert page1.data.count(b"PAGED-ITEM-") == 12
    assert b"Page 1 of 2 (15 listings)" in page1.data

    page2 = client.get("/listings?page=2")
    assert page2.data.count(b"PAGED-ITEM-") == 3


def test_pagination_preserves_filters(client, db_session):
    seller = _seller()
    for i in range(13):
        _approved(seller, f"FILTERED-{i:02d}")

    resp = client.get("/listings?brand=B&page=1")
    assert resp.status_code == 200
    # The next-page link carries the brand filter along.
    assert b"page=2" in resp.data and b"brand=B" in resp.data


def test_hostile_page_values_are_safe(client, db_session):
    seller = _seller()
    _approved(seller, "SINGLETON")

    for hostile in ("abc", "-5", "999999", "1;DROP TABLE"):
        resp = client.get(f"/listings?page={hostile}")
        assert resp.status_code == 200


def test_average_rating_shows_on_index_and_detail(client, db_session):
    seller = _seller()
    listing = _approved(seller, "RATED-BAG")

    for rating in (5, 4):
        buyer = User(email=f"b{time.time_ns()}@example.com", password_hash="x",
                     role=UserRole.BUYER, status="active")
        db.session.add(buyer)
        db.session.commit()
        order = Order(buyer_id=buyer.id, listing_id=listing.id,
                      committed_price=listing.price,
                      workflow_status=WorkflowStatus.SOLD)
        db.session.add(order)
        db.session.commit()
        db.session.add(Review(order_id=order.id, buyer_id=buyer.id,
                              listing_id=listing.id, rating=rating))
        db.session.commit()

    index = client.get("/listings")
    assert "★ 4.5".encode("utf-8") in index.data
    assert b"(2 reviews)" in index.data

    detail = client.get(f"/listings/{listing.id}")
    assert "★ 4.5".encode("utf-8") in detail.data
