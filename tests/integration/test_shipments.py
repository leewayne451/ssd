"""M9 — shipment tracking by sellers (FR-10 / SFR-10, D1 UC-05).

A seller records a tracking reference and moves their own order
awaiting_shipment -> shipped through the audited workflow state machine.
Ownership is the core control: Seller A can never ship Seller B's order,
buyers cannot ship at all, and buyers read tracking only on their own order.
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
from app.models.shipment import Shipment
from app.models.user import User


def _listing_for(seller):
    listing = ProductListing(
        seller_id=seller.id, title="Ship me", description="d",
        category="watches", brand="B", price=250.0,
        condition=ListingCondition.PRE_OWNED,
        approval_status=ApprovalStatus.APPROVED,
    )
    db.session.add(listing)
    db.session.commit()
    return listing


def _buyer_order(listing, workflow=WorkflowStatus.AWAITING_SHIPMENT):
    buyer = User(email=f"buyer{time.time_ns()}@example.com", password_hash="x",
                 role=UserRole.BUYER, status="active")
    db.session.add(buyer)
    db.session.commit()
    order = Order(
        buyer_id=buyer.id, listing_id=listing.id,
        committed_price=listing.price, workflow_status=workflow,
    )
    db.session.add(order)
    db.session.commit()
    return buyer, order


# ------------------- happy path ---------------------------------------------

def test_seller_marks_own_order_shipped_with_tracking(client, login_as):
    seller = login_as("shipseller@example.com", role=UserRole.SELLER)
    listing = _listing_for(seller)
    _, order = _buyer_order(listing)

    resp = client.post(
        f"/orders/{order.id}/shipment",
        data={"tracking_number": "SG-TRACK-0001"},
        follow_redirects=True,
    )
    assert resp.status_code == 200

    db.session.refresh(order)
    assert order.workflow_status.value == "shipped"

    shipment = Shipment.query.filter_by(order_id=order.id).one()
    assert shipment.tracking_number == "SG-TRACK-0001"
    assert shipment.shipped_at is not None

    # The transition went through the audited state machine (FSR-11)
    assert AuditLog.query.filter_by(
        action_type="workflow_transition", target_id=order.id
    ).first() is not None


def test_sales_page_lists_only_own_orders(client, db_session, login_as):
    other_seller = User(email="rival@example.com", password_hash="x",
                        role=UserRole.SELLER, status="active")
    db.session.add(other_seller)
    db.session.commit()
    other_listing = ProductListing(
        seller_id=other_seller.id, title="RIVAL-ONLY-ITEM", description="d",
        category="bags", brand="B", price=10.0,
        condition=ListingCondition.NEW, approval_status=ApprovalStatus.APPROVED,
    )
    db.session.add(other_listing)
    db.session.commit()
    _buyer_order(other_listing)

    me = login_as("mysales@example.com", role=UserRole.SELLER)
    mine = _listing_for(me)
    _buyer_order(mine)

    resp = client.get("/seller/sales")
    assert resp.status_code == 200
    assert b"Ship me" in resp.data
    assert b"RIVAL-ONLY-ITEM" not in resp.data


# ------------------- ownership / role gates (SFR-10) -------------------------

def test_other_seller_cannot_ship_someone_elses_order(client, db_session, login_as):
    owner = User(email="realowner@example.com", password_hash="x",
                 role=UserRole.SELLER, status="active")
    db.session.add(owner)
    db.session.commit()
    listing = _listing_for(owner)
    _, order = _buyer_order(listing)

    login_as("intruder@example.com", role=UserRole.SELLER)
    client.post(f"/orders/{order.id}/shipment",
                data={"tracking_number": "HIJACK-1"}, follow_redirects=True)

    db.session.refresh(order)
    assert order.workflow_status.value == "awaiting_shipment"
    assert Shipment.query.filter_by(order_id=order.id).count() == 0


def test_buyer_cannot_hit_shipment_endpoint(client, db_session, login_as):
    seller = User(email="passive@example.com", password_hash="x",
                  role=UserRole.SELLER, status="active")
    db.session.add(seller)
    db.session.commit()
    listing = _listing_for(seller)
    _, order = _buyer_order(listing)

    login_as("sneakybuyer@example.com")  # buyer role
    resp = client.post(f"/orders/{order.id}/shipment",
                       data={"tracking_number": "X"})
    assert resp.status_code == 403

    assert client.get("/seller/sales").status_code == 403
    assert client.post("/orders/1/shipment", data={}).status_code == 403


def test_anonymous_gets_401(client, db_session):
    assert client.post("/orders/1/shipment", data={}).status_code == 401
    assert client.get("/seller/sales").status_code == 401


# ------------------- state / input validation --------------------------------

def test_cannot_ship_from_wrong_state(client, login_as):
    seller = login_as("early@example.com", role=UserRole.SELLER)
    listing = _listing_for(seller)
    _, order = _buyer_order(listing, workflow=WorkflowStatus.COMMITTED)

    client.post(f"/orders/{order.id}/shipment",
                data={"tracking_number": "TOO-EARLY"}, follow_redirects=True)

    db.session.refresh(order)
    assert order.workflow_status.value == "committed"
    assert Shipment.query.filter_by(order_id=order.id).count() == 0


def test_tracking_reference_required(client, login_as):
    seller = login_as("notrack@example.com", role=UserRole.SELLER)
    listing = _listing_for(seller)
    _, order = _buyer_order(listing)

    client.post(f"/orders/{order.id}/shipment",
                data={"tracking_number": "   "}, follow_redirects=True)

    db.session.refresh(order)
    assert order.workflow_status.value == "awaiting_shipment"
    assert Shipment.query.filter_by(order_id=order.id).count() == 0


# ------------------- buyer-visible tracking ----------------------------------

def test_buyer_sees_tracking_on_own_order(app, client, db_session):
    from app.services.auth_service import register_user
    from app.services import shipment_service

    seller = User(email="track@example.com", password_hash="x",
                  role=UserRole.SELLER, status="active")
    db.session.add(seller)
    db.session.commit()
    listing = _listing_for(seller)

    buyer, err = register_user("watching@example.com", "MySecureP@ssw0rd!2026")
    assert err is None
    order = Order(buyer_id=buyer.id, listing_id=listing.id,
                  committed_price=listing.price,
                  workflow_status=WorkflowStatus.AWAITING_SHIPMENT)
    db.session.add(order)
    db.session.commit()

    shipment_service.mark_shipped(seller, order.id, "SG-VISIBLE-42")

    client.post("/auth/login",
                data={"email": "watching@example.com",
                      "password": "MySecureP@ssw0rd!2026"},
                follow_redirects=True)
    resp = client.get(f"/orders/{order.id}")
    assert resp.status_code == 200
    assert b"SG-VISIBLE-42" in resp.data
