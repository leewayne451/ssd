"""Seller "My listings" overview (FR-07 usability — UI-audit item 5).

Public pages hide unapproved listings, so sellers need an own-scoped page
that shows every listing they own, whatever its approval state. The query is
scoped by seller_id: another seller's items can never appear.
"""

import time

from app.extensions import db
from app.models.enums import ApprovalStatus, ListingCondition, UserRole
from app.models.product_listing import ProductListing
from app.models.user import User


def _listing(seller, title, approval):
    listing = ProductListing(
        seller_id=seller.id, title=title, description="d",
        category="bags", brand="B", price=10.0,
        condition=ListingCondition.PRE_OWNED, approval_status=approval,
    )
    db.session.add(listing)
    db.session.commit()
    return listing


def test_seller_sees_all_own_listings_including_pending(client, login_as):
    seller = login_as("owner-lister@example.com", role=UserRole.SELLER)
    _listing(seller, "MY-APPROVED-BAG", ApprovalStatus.APPROVED)
    _listing(seller, "MY-PENDING-BAG", ApprovalStatus.PENDING)
    _listing(seller, "MY-REJECTED-BAG", ApprovalStatus.REJECTED)

    resp = client.get("/seller/listings")
    assert resp.status_code == 200
    assert b"MY-APPROVED-BAG" in resp.data
    assert b"MY-PENDING-BAG" in resp.data
    assert b"MY-REJECTED-BAG" in resp.data


def test_other_sellers_listings_never_appear(client, db_session, login_as):
    rival = User(email=f"rival{time.time_ns()}@example.com", password_hash="x",
                 role=UserRole.SELLER, status="active")
    db.session.add(rival)
    db.session.commit()
    _listing(rival, "RIVAL-SECRET-DRAFT", ApprovalStatus.PENDING)

    login_as("cleanseller@example.com", role=UserRole.SELLER)
    resp = client.get("/seller/listings")
    assert resp.status_code == 200
    assert b"RIVAL-SECRET-DRAFT" not in resp.data


def test_role_gate_on_my_listings(client, db_session, login_as):
    assert client.get("/seller/listings").status_code == 401
    login_as("justabuyer@example.com")
    assert client.get("/seller/listings").status_code == 403
