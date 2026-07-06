"""Listing availability lifecycle (SFR-09 — UI-audit item 16).

One-of-a-kind luxury items: committing an order takes the LISTING out of
circulation too. Before this fix a listing stayed 'available' forever — two
buyers could commit to the same item and sold items showed no state at all.
The listing now mirrors the order through the D1 H-3 workflow.
"""

import uuid

from app.extensions import db
from app.models.enums import (
    ApprovalStatus,
    ListingCondition,
    UserRole,
    WorkflowStatus,
)
from app.models.order import Order
from app.models.product_listing import ProductListing
from app.models.user import User
from app.services import cart_service, order_service, workflow_service


def _user(role=UserRole.BUYER):
    # uuid, not time_ns: Windows' clock tick is coarse enough that two rapid
    # calls can collide on the unique-email constraint.
    user = User(email=f"u{uuid.uuid4().hex}@example.com", password_hash="x",
                role=role, status="active")
    db.session.add(user)
    db.session.commit()
    return user


def _listing(workflow=WorkflowStatus.AVAILABLE):
    seller = _user(UserRole.SELLER)
    listing = ProductListing(
        seller_id=seller.id, title="One of a kind", description="d",
        category="watches", brand="B", price=500.0,
        condition=ListingCondition.PRE_OWNED,
        approval_status=ApprovalStatus.APPROVED,
        workflow_status=workflow,
    )
    db.session.add(listing)
    db.session.commit()
    return listing


def test_commit_marks_listing_committed(db_session):
    buyer = _user()
    listing = _listing()
    cart_service.add_item(buyer, listing.id)

    orders = order_service.place_orders_from_cart(buyer)
    assert len(orders) == 1

    db.session.refresh(listing)
    assert listing.workflow_status.value == "committed"


def test_second_buyer_cannot_commit_same_item(db_session):
    first, second = _user(), _user()
    listing = _listing()

    # Both buyers cart the item while it is still available.
    cart_service.add_item(first, listing.id)
    cart_service.add_item(second, listing.id)

    assert len(order_service.place_orders_from_cart(first)) == 1
    # The second commit finds the item already committed and skips it.
    assert order_service.place_orders_from_cart(second) == []
    assert Order.query.filter_by(listing_id=listing.id).count() == 1


def test_cart_add_rejected_once_item_is_reserved(db_session):
    buyer = _user()
    listing = _listing(workflow=WorkflowStatus.COMMITTED)

    try:
        cart_service.add_item(buyer, listing.id)
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_workflow_transitions_mirror_to_listing(db_session):
    buyer = _user()
    listing = _listing()
    cart_service.add_item(buyer, listing.id)
    order = order_service.place_orders_from_cart(buyer)[0]

    admin = _user(UserRole.ADMIN)
    for status in ("awaiting_shipment", "shipped", "under_authentication",
                   "authenticated", "sold"):
        workflow_service.transition_order(order, status, admin)

    db.session.refresh(listing)
    assert listing.workflow_status.value == "sold"


def test_sold_listing_page_hides_add_to_cart(client, db_session, login_as):
    listing = _listing(workflow=WorkflowStatus.SOLD)
    login_as("windowshopper@example.com")

    resp = client.get(f"/listings/{listing.id}")
    assert resp.status_code == 200
    assert b"has been <strong>sold</strong>" in resp.data
    assert b"Add to cart" not in resp.data


def test_reserved_listing_page_hides_add_to_cart(client, db_session, login_as):
    listing = _listing(workflow=WorkflowStatus.UNDER_AUTHENTICATION)
    login_as("latecomer@example.com")

    resp = client.get(f"/listings/{listing.id}")
    assert resp.status_code == 200
    assert b"reserved" in resp.data
    assert b"Add to cart" not in resp.data
