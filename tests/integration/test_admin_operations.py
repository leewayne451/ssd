"""M5 — admin operations: suspend, moderation, authentication review, audit (T-32..T-37).

All admin routes are gated by role_required("admin") + admin_2fa_required, so
each test enrols + verifies a 2FA admin before acting, and every privileged
action is asserted to leave an AuditLog row (FSR-11/12, NFSR-08).
"""

import time

import pytest

from app.extensions import db
from app.models.audit_log import AuditLog
from app.models.enums import (
    AccountStatus,
    ApprovalStatus,
    AuthenticationResult,
    ListingCondition,
    UserRole,
    WorkflowStatus,
)
from app.models.authentication_review import AuthenticationReview
from app.models.order import Order
from app.models.product_listing import ProductListing
from app.models.user import User
from app.security import admin_2fa


def _make_admin_verified(client):
    """Create an enrolled admin and mark this client's session 2FA-verified."""
    secret = admin_2fa.generate_secret()
    admin = User(
        email=f"admin{time.time_ns()}@example.com",
        password_hash="x",
        role=UserRole.ADMIN,
        status="active",
        totp_secret=secret,
        totp_enabled=True,
    )
    db.session.add(admin)
    db.session.commit()
    with client.session_transaction() as sess:
        sess["user_id"] = admin.id
        sess["role"] = "admin"
        sess[admin_2fa.SESSION_2FA_FLAG] = True
    return admin


def _seller_and_listing(approval=ApprovalStatus.PENDING):
    seller = User(email=f"s{time.time_ns()}@example.com", password_hash="x",
                  role=UserRole.SELLER, status="active")
    db.session.add(seller)
    db.session.commit()
    listing = ProductListing(
        seller_id=seller.id, title="Moderate me", description="d",
        category="bags", brand="B", price=10.0,
        condition=ListingCondition.PRE_OWNED, approval_status=approval,
    )
    db.session.add(listing)
    db.session.commit()
    return seller, listing


# ------------------- FR-13 suspension (T-32, T-33) --------------------------

def test_admin_suspend_user_writes_audit_row(client, db_session):
    """T-32: suspend flips status and records the acting admin."""
    admin = _make_admin_verified(client)
    victim = User(email="victim@example.com", password_hash="x",
                  role=UserRole.BUYER, status="active")
    db.session.add(victim)
    db.session.commit()

    resp = client.post(f"/admin/users/{victim.id}/suspend")
    assert resp.status_code == 302

    db.session.refresh(victim)
    assert victim.status == AccountStatus.SUSPENDED

    row = AuditLog.query.filter_by(action_type="user_suspended", target_id=victim.id).first()
    assert row is not None
    assert row.actor_user_id == admin.id


def test_non_admin_cannot_suspend(client, db_session, make_user):
    """T-33: a buyer hitting the admin action is blocked (403)."""
    buyer = make_user("np-buyer@test.local", role=UserRole.BUYER)
    victim = make_user("np-victim@test.local", role=UserRole.BUYER)
    with client.session_transaction() as sess:
        sess["user_id"] = buyer.id
        sess["role"] = "buyer"

    resp = client.post(f"/admin/users/{victim.id}/suspend")
    assert resp.status_code == 403
    db.session.refresh(victim)
    assert victim.status == AccountStatus.ACTIVE


def test_admin_without_2fa_cannot_suspend(client, db_session, make_user):
    """Admin role alone is not enough — the 2FA gate redirects (302, not action)."""
    admin = make_user("no2fa-admin@test.local", role=UserRole.ADMIN)
    victim = make_user("no2fa-victim@test.local", role=UserRole.BUYER)
    with client.session_transaction() as sess:
        sess["user_id"] = admin.id
        sess["role"] = "admin"  # but no SESSION_2FA_FLAG

    resp = client.post(f"/admin/users/{victim.id}/suspend", follow_redirects=False)
    assert resp.status_code == 302
    assert "2fa" in resp.headers["Location"]
    db.session.refresh(victim)
    assert victim.status == AccountStatus.ACTIVE


# ------------------- FR-14 listing moderation (T-34) ------------------------

def test_admin_approve_and_reject_listing_with_audit(client, db_session):
    """T-34: approve/reject change approval_status and write audit rows."""
    admin = _make_admin_verified(client)
    _, pending = _seller_and_listing(ApprovalStatus.PENDING)

    client.post(f"/admin/listings/{pending.id}/approve")
    db.session.refresh(pending)
    assert pending.approval_status == ApprovalStatus.APPROVED
    assert AuditLog.query.filter_by(action_type="listing_approved", target_id=pending.id).first()

    _, other = _seller_and_listing(ApprovalStatus.PENDING)
    client.post(f"/admin/listings/{other.id}/reject", data={"reason": "counterfeit"})
    db.session.refresh(other)
    assert other.approval_status == ApprovalStatus.REJECTED
    assert other.is_active is False
    assert AuditLog.query.filter_by(action_type="listing_rejected", target_id=other.id).first()


def test_buyer_can_report_listing(client, db_session, login_as):
    """FR-14 report mechanism: a logged-in buyer flags a listing."""
    _, listing = _seller_and_listing(ApprovalStatus.APPROVED)
    login_as("reporter@example.com")

    resp = client.post(f"/listings/{listing.id}/report", data={"reason": "fake"}, follow_redirects=True)
    assert resp.status_code == 200
    db.session.refresh(listing)
    assert listing.reported is True


# ------------------- authentication review (T-35, T-36) ---------------------

def test_admin_authentication_review_flips_state_and_records(client, db_session):
    """T-35: authentic outcome -> authenticated + review row + audit."""
    admin = _make_admin_verified(client)
    _, listing = _seller_and_listing(ApprovalStatus.APPROVED)
    buyer = User(email="ar-buyer@example.com", password_hash="x",
                 role=UserRole.BUYER, status="active")
    db.session.add(buyer)
    db.session.commit()
    order = Order(buyer_id=buyer.id, listing_id=listing.id, committed_price=10.0,
                  workflow_status=WorkflowStatus.UNDER_AUTHENTICATION)
    db.session.add(order)
    db.session.commit()

    resp = client.post(f"/admin/orders/{order.id}/authenticate",
                       data={"outcome": "authentic", "notes": "genuine hallmark"})
    assert resp.status_code == 302

    db.session.refresh(order)
    assert order.workflow_status == WorkflowStatus.AUTHENTICATED
    review = AuthenticationReview.query.filter_by(order_id=order.id).one()
    assert review.result == AuthenticationResult.AUTHENTIC
    assert review.reviewed_by_admin_id == admin.id
    assert AuditLog.query.filter_by(action_type="authentication_review", target_id=order.id).first()


def test_counterfeit_outcome_rejects_order(client, db_session):
    admin = _make_admin_verified(client)
    _, listing = _seller_and_listing(ApprovalStatus.APPROVED)
    buyer = User(email="cf-buyer@example.com", password_hash="x",
                 role=UserRole.BUYER, status="active")
    db.session.add(buyer)
    db.session.commit()
    order = Order(buyer_id=buyer.id, listing_id=listing.id, committed_price=10.0,
                  workflow_status=WorkflowStatus.UNDER_AUTHENTICATION)
    db.session.add(order)
    db.session.commit()

    client.post(f"/admin/orders/{order.id}/authenticate", data={"outcome": "counterfeit"})
    db.session.refresh(order)
    assert order.workflow_status == WorkflowStatus.REJECTED


def test_seller_cannot_authenticate_via_admin_route(client, db_session, make_user):
    """T-36: sellers can't reach the admin authentication route (403)."""
    seller = make_user("auth-seller@test.local", role=UserRole.SELLER)
    with client.session_transaction() as sess:
        sess["user_id"] = seller.id
        sess["role"] = "seller"

    resp = client.post("/admin/orders/1/authenticate", data={"outcome": "authentic"})
    assert resp.status_code == 403


# ------------------- FR-15 workflow update (T-37) ---------------------------

def test_admin_workflow_update_writes_audit(client, db_session):
    """T-37: admin FR-15 status change goes through the audited state machine."""
    admin = _make_admin_verified(client)
    _, listing = _seller_and_listing(ApprovalStatus.APPROVED)
    buyer = User(email="wf-buyer@example.com", password_hash="x",
                 role=UserRole.BUYER, status="active")
    db.session.add(buyer)
    db.session.commit()
    order = Order(buyer_id=buyer.id, listing_id=listing.id, committed_price=10.0,
                  workflow_status=WorkflowStatus.COMMITTED)
    db.session.add(order)
    db.session.commit()

    resp = client.post(f"/admin/orders/{order.id}/status", data={"new_status": "awaiting_shipment"})
    assert resp.status_code == 302
    db.session.refresh(order)
    assert order.workflow_status == WorkflowStatus.AWAITING_SHIPMENT
    assert AuditLog.query.filter_by(action_type="workflow_transition", target_id=order.id).first()
