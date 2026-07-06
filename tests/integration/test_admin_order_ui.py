"""Admin order surface + buyer order page (FR-15 UI, refunds, SFR-14).

Covers the follow-up UI audit items: the manual workflow-update form is
reachable and drives the audited state machine; refunds (D1 §9.3.4
paid -> refunded) exist as an admin-only route; authentication verdicts show
to admins WITH notes and to buyers WITHOUT notes (SFR-14); the buyer order
page surfaces the OrderStatusHistory timeline.
"""

import time

from app.extensions import db
from app.models.audit_log import AuditLog
from app.models.enums import (
    ApprovalStatus,
    ListingCondition,
    PaymentStatus,
    UserRole,
    WorkflowStatus,
)
from app.models.order import Order
from app.models.order_status_history import OrderStatusHistory
from app.models.product_listing import ProductListing
from app.models.user import User
from app.security import admin_2fa
from app.services import admin_service


def _make_admin_verified(client):
    secret = admin_2fa.generate_secret()
    admin = User(
        email=f"admin{time.time_ns()}@example.com", password_hash="x",
        role=UserRole.ADMIN, status="active",
        totp_secret=secret, totp_enabled=True,
    )
    db.session.add(admin)
    db.session.commit()
    with client.session_transaction() as sess:
        sess["user_id"] = admin.id
        sess["role"] = "admin"
        sess[admin_2fa.SESSION_2FA_FLAG] = True
    return admin


def _order(workflow=WorkflowStatus.COMMITTED, payment=PaymentStatus.PENDING, buyer=None):
    if buyer is None:
        buyer = User(email=f"b{time.time_ns()}@example.com", password_hash="x",
                     role=UserRole.BUYER, status="active")
        db.session.add(buyer)
        db.session.commit()
    seller = User(email=f"s{time.time_ns()}@example.com", password_hash="x",
                  role=UserRole.SELLER, status="active")
    db.session.add(seller)
    db.session.commit()
    listing = ProductListing(
        seller_id=seller.id, title="Admin UI item", description="d",
        category="bags", brand="B", price=10.0,
        condition=ListingCondition.PRE_OWNED,
        approval_status=ApprovalStatus.APPROVED,
    )
    db.session.add(listing)
    db.session.commit()
    order = Order(buyer_id=buyer.id, listing_id=listing.id,
                  committed_price=listing.price,
                  workflow_status=workflow, payment_status=payment)
    db.session.add(order)
    db.session.commit()
    return order


# ------------------- FR-15: workflow-update form is reachable ---------------

def test_admin_orders_page_offers_workflow_update_form(client, db_session):
    _make_admin_verified(client)
    order = _order(workflow=WorkflowStatus.COMMITTED)

    resp = client.get("/admin/orders")
    assert resp.status_code == 200
    # A form posts to the manual-update route with only legal next states.
    assert f"/admin/orders/{order.id}/status".encode() in resp.data
    assert b'name="new_status"' in resp.data
    assert b"awaiting_shipment" in resp.data


# ------------------- refunds (D1 9.3.4 paid -> refunded) --------------------

def test_admin_refunds_paid_order_with_audit(client, db_session):
    admin = _make_admin_verified(client)
    order = _order(workflow=WorkflowStatus.SOLD, payment=PaymentStatus.PAID)

    resp = client.post(f"/admin/orders/{order.id}/refund")
    assert resp.status_code == 302

    db.session.refresh(order)
    assert order.payment_status.value == "refunded"
    row = AuditLog.query.filter_by(action_type="order_refunded", target_id=order.id).first()
    assert row is not None and row.actor_user_id == admin.id


def test_refund_rejected_when_payment_not_paid(client, db_session):
    _make_admin_verified(client)
    order = _order(payment=PaymentStatus.PENDING)

    client.post(f"/admin/orders/{order.id}/refund", follow_redirects=True)
    db.session.refresh(order)
    assert order.payment_status.value == "pending"


def test_non_admin_cannot_refund(client, db_session, login_as):
    order = _order(workflow=WorkflowStatus.SOLD, payment=PaymentStatus.PAID)
    login_as("norefund@example.com")
    assert client.post(f"/admin/orders/{order.id}/refund").status_code == 403
    db.session.refresh(order)
    assert order.payment_status.value == "paid"


# ------------------- SFR-14: verdict visibility split -----------------------

def test_authentication_notes_admin_only(client, db_session, login_as):
    buyer = login_as("verdictbuyer@example.com")
    order = _order(workflow=WorkflowStatus.UNDER_AUTHENTICATION, buyer=buyer)

    admin = User(email=f"rev{time.time_ns()}@example.com", password_hash="x",
                 role=UserRole.ADMIN, status="active")
    db.session.add(admin)
    db.session.commit()
    admin_service.record_authentication_review(
        admin, order.id, is_authentic=True, notes="INTERNAL-NOTE-serial-checked"
    )

    # Buyer sees the verdict but never the moderation notes (SFR-14).
    buyer_page = client.get(f"/orders/{order.id}")
    assert buyer_page.status_code == 200
    assert b"authentic" in buyer_page.data
    assert b"INTERNAL-NOTE-serial-checked" not in buyer_page.data

    # Admin sees verdict AND notes on the admin surface.
    admin_client_admin = _make_admin_verified(client)  # rebind session as admin
    admin_page = client.get("/admin/orders")
    assert admin_page.status_code == 200
    assert b"INTERNAL-NOTE-serial-checked" in admin_page.data


# ------------------- order history timeline ---------------------------------

def test_buyer_sees_order_history_timeline(client, db_session, login_as):
    buyer = login_as("timeline@example.com")
    order = _order(workflow=WorkflowStatus.SHIPPED, buyer=buyer)
    for old, new in [("", "committed"), ("committed", "awaiting_shipment"),
                     ("awaiting_shipment", "shipped")]:
        db.session.add(OrderStatusHistory(order_id=order.id, actor_user_id=buyer.id,
                                          old_status=old, new_status=new))
    db.session.commit()

    resp = client.get(f"/orders/{order.id}")
    assert resp.status_code == 200
    assert b"Order history" in resp.data
    assert b"awaiting shipment" in resp.data
