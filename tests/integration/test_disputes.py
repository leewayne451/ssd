"""M11 — dispute resolution workflow (FR-17 / SFR-17, D1 UC-06).

Buyers raise disputes only on their OWN orders (verified server-side);
admins close them (resolved/dismissed) from the role+2FA-gated queue and
every decision is audited. Buyers see only their own disputes.
"""

import time

from app.extensions import db
from app.models.audit_log import AuditLog
from app.models.dispute import Dispute
from app.models.enums import (
    ApprovalStatus,
    DisputeStatus,
    ListingCondition,
    UserRole,
    WorkflowStatus,
)
from app.models.order import Order
from app.models.product_listing import ProductListing
from app.models.user import User
from app.security import admin_2fa
from app.services import dispute_service


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


def _order_for(buyer, workflow=WorkflowStatus.SHIPPED):
    seller = User(email=f"seller{time.time_ns()}@example.com", password_hash="x",
                  role=UserRole.SELLER, status="active")
    db.session.add(seller)
    db.session.commit()
    listing = ProductListing(
        seller_id=seller.id, title="Disputed item", description="d",
        category="bags", brand="B", price=50.0,
        condition=ListingCondition.PRE_OWNED,
        approval_status=ApprovalStatus.APPROVED,
    )
    db.session.add(listing)
    db.session.commit()
    order = Order(buyer_id=buyer.id, listing_id=listing.id,
                  committed_price=listing.price, workflow_status=workflow)
    db.session.add(order)
    db.session.commit()
    return order


# ------------------- raising (SFR-17 ownership) ------------------------------

def test_buyer_raises_dispute_on_own_order(client, login_as):
    buyer = login_as("unhappy@example.com")
    order = _order_for(buyer)

    resp = client.post(
        f"/orders/{order.id}/dispute",
        data={"reason": "Item arrived damaged."},
        follow_redirects=True,
    )
    assert resp.status_code == 200

    dispute = Dispute.query.filter_by(order_id=order.id).one()
    assert dispute.buyer_id == buyer.id
    assert dispute.status == DisputeStatus.OPEN

    assert AuditLog.query.filter_by(
        action_type="dispute_raised", target_id=dispute.id
    ).first() is not None


def test_buyer_cannot_dispute_someone_elses_order(client, db_session, login_as):
    victim = User(email="victimbuyer@example.com", password_hash="x",
                  role=UserRole.BUYER, status="active")
    db.session.add(victim)
    db.session.commit()
    order = _order_for(victim)

    login_as("meddler@example.com")
    client.post(f"/orders/{order.id}/dispute",
                data={"reason": "not mine"}, follow_redirects=True)
    assert Dispute.query.filter_by(order_id=order.id).count() == 0


def test_anonymous_cannot_raise_or_list_disputes(client, db_session):
    assert client.post("/orders/1/dispute", data={"reason": "x"}).status_code == 401
    assert client.get("/disputes").status_code == 401


def test_one_live_dispute_per_order(client, login_as):
    buyer = login_as("persistent@example.com")
    order = _order_for(buyer)

    for reason in ("first", "second"):
        client.post(f"/orders/{order.id}/dispute",
                    data={"reason": reason}, follow_redirects=True)
    assert Dispute.query.filter_by(order_id=order.id).count() == 1


def test_empty_reason_rejected(client, login_as):
    buyer = login_as("silent@example.com")
    order = _order_for(buyer)

    client.post(f"/orders/{order.id}/dispute",
                data={"reason": "   "}, follow_redirects=True)
    assert Dispute.query.filter_by(order_id=order.id).count() == 0


# ------------------- buyer view is own-only ----------------------------------

def test_buyer_sees_only_own_disputes(client, db_session, login_as):
    other = User(email="otherdisputer@example.com", password_hash="x",
                 role=UserRole.BUYER, status="active")
    db.session.add(other)
    db.session.commit()
    other_order = _order_for(other)
    dispute_service.raise_dispute(other, other_order.id, "OTHER-BUYER-SECRET")

    mine = login_as("minedisputes@example.com")
    my_order = _order_for(mine)
    client.post(f"/orders/{my_order.id}/dispute",
                data={"reason": "my own problem"}, follow_redirects=True)

    resp = client.get("/disputes")
    assert resp.status_code == 200
    assert b"my own problem" in resp.data
    assert b"OTHER-BUYER-SECRET" not in resp.data


# ------------------- admin resolution (FSR-10) -------------------------------

def test_admin_resolves_dispute_with_notes_and_audit(client, db_session):
    buyer = User(email="resolved@example.com", password_hash="x",
                 role=UserRole.BUYER, status="active")
    db.session.add(buyer)
    db.session.commit()
    order = _order_for(buyer)
    dispute, _ = dispute_service.raise_dispute(buyer, order.id, "broken clasp")

    admin = _make_admin_verified(client)
    resp = client.post(
        f"/admin/disputes/{dispute.id}/resolve",
        data={"outcome": "resolved", "notes": "Refund issued."},
    )
    assert resp.status_code == 302

    db.session.refresh(dispute)
    assert dispute.status == DisputeStatus.RESOLVED
    assert dispute.resolved_by_admin_id == admin.id
    assert dispute.resolution_notes == "Refund issued."
    assert dispute.resolved_at is not None

    row = AuditLog.query.filter_by(
        action_type="dispute_resolved", target_id=dispute.id
    ).first()
    assert row is not None and row.actor_user_id == admin.id


def test_admin_invalid_outcome_rejected(client, db_session):
    buyer = User(email="weird@example.com", password_hash="x",
                 role=UserRole.BUYER, status="active")
    db.session.add(buyer)
    db.session.commit()
    order = _order_for(buyer)
    dispute, _ = dispute_service.raise_dispute(buyer, order.id, "hmm")

    _make_admin_verified(client)
    client.post(f"/admin/disputes/{dispute.id}/resolve",
                data={"outcome": "obliterated"}, follow_redirects=True)

    db.session.refresh(dispute)
    assert dispute.status == DisputeStatus.OPEN


def test_non_admin_cannot_resolve(client, db_session, login_as):
    buyer = User(email="hopefulbuyer@example.com", password_hash="x",
                 role=UserRole.BUYER, status="active")
    db.session.add(buyer)
    db.session.commit()
    order = _order_for(buyer)
    dispute, _ = dispute_service.raise_dispute(buyer, order.id, "please fix")

    login_as("plainuser@example.com")
    assert client.get("/admin/disputes").status_code == 403
    assert client.post(
        f"/admin/disputes/{dispute.id}/resolve",
        data={"outcome": "resolved"},
    ).status_code == 403

    db.session.refresh(dispute)
    assert dispute.status == DisputeStatus.OPEN
