"""M4 — D1 H-3 conformance for the workflow + simulated checkout (T-23..T-28, T-30, T-31).

The transition matrix test (T-23) locks the state machine to Deliverable One
exactly: any future edit that adds or removes an edge fails this test.
"""

import pytest

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
from app.models.security_event import SecurityEvent
from app.services import checkout_service, workflow_service
from app.services.cart_service import add_item

# The authoritative D1 H-3 edges (committed/awaiting -> rejected are the
# admin compliance-rejection edges).
D1_EDGES = {
    ("committed", "awaiting_shipment"),
    ("committed", "rejected"),
    ("awaiting_shipment", "shipped"),
    ("awaiting_shipment", "rejected"),
    ("shipped", "under_authentication"),
    ("under_authentication", "authenticated"),
    ("under_authentication", "rejected"),
    ("authenticated", "sold"),
}

_ORDER_STATES = [s.value for s in WorkflowStatus if s != WorkflowStatus.AVAILABLE]


@pytest.mark.parametrize("old", _ORDER_STATES)
@pytest.mark.parametrize("new", [s.value for s in WorkflowStatus])
def test_transition_matrix_exactly_matches_d1_h3(old, new):
    """T-23: the full matrix — allowed iff the edge exists in D1 H-3."""
    expected = (old, new) in D1_EDGES
    assert workflow_service.can_transition(old, new) is expected


def test_shipped_to_sold_direct_is_rejected(client, db_session, admin_user, order):
    """T-24: even an admin cannot bypass authentication (shipped -> sold)."""
    order.workflow_status = WorkflowStatus.SHIPPED
    db.session.commit()

    with pytest.raises(ValueError, match="illegal workflow transition"):
        workflow_service.transition_order(order, "sold", admin_user)


def test_seller_cannot_transition_other_sellers_order(client, db_session, make_user, order):
    """T-25: role is not enough — the actor must own THIS order's listing (CTRL-002)."""
    seller_b = make_user("rival-seller@test.local", role=UserRole.SELLER)

    with pytest.raises(PermissionError, match="does not own"):
        workflow_service.transition_order(order, "awaiting_shipment", seller_b)

    event = SecurityEvent.query.filter_by(event_type="workflow_transition_rejected").first()
    assert event is not None


def test_transition_writes_audit_log_row(client, db_session, seller_user, order):
    """T-37 precursor: successful transitions land in the AUDIT log (not just history)."""
    workflow_service.transition_order(order, "awaiting_shipment", seller_user)

    row = AuditLog.query.filter_by(action_type="workflow_transition", target_id=order.id).first()
    assert row is not None
    assert "awaiting_shipment" in (row.details or "")


def test_transition_route_rejects_invalid_status_strings(client, login_as, approved_listing, db_session):
    """T-30: arbitrary status strings die at the route with a 400."""
    buyer = login_as("route-guard@example.com")
    order = Order(
        buyer_id=buyer.id, listing_id=approved_listing.id,
        committed_price=approved_listing.price,
        workflow_status=WorkflowStatus.COMMITTED,
    )
    db_session.add(order)
    db_session.commit()

    resp = client.post(f"/orders/{order.id}/transition", data={"new_status": "sold'; DROP TABLE orders;--"})
    assert resp.status_code == 400
    resp = client.post(f"/orders/{order.id}/transition", data={})
    assert resp.status_code == 400


def test_commit_skips_unapproved_listing(client, db_session, make_user, buyer_user):
    """T-31: a stale cart cannot commit to a pending/unapproved item (SFR-09)."""
    from app.models.product_listing import ProductListing
    from app.services.order_service import place_orders_from_cart

    seller = make_user("pending-seller@test.local", role=UserRole.SELLER)
    pending = ProductListing(
        seller_id=seller.id, title="Not yet approved", description="x",
        category="watches", brand="B", price=10.0,
        condition=ListingCondition.PRE_OWNED,
        approval_status=ApprovalStatus.PENDING,
    )
    db.session.add(pending)
    db.session.commit()

    add_item(buyer_user, pending.id, 1)
    created = place_orders_from_cart(buyer_user)
    assert created == []
    assert Order.query.filter_by(listing_id=pending.id).first() is None


# --------------------------- simulated checkout ------------------------------

def _make_order_for(buyer, listing, db_session, workflow=WorkflowStatus.AUTHENTICATED):
    order = Order(
        buyer_id=buyer.id, listing_id=listing.id,
        committed_price=listing.price, workflow_status=workflow,
    )
    db_session.add(order)
    db_session.commit()
    return order


def test_checkout_happy_path(client, login_as, approved_listing, db_session):
    """T-26: authenticated item -> checkout marks paid + sold; no card fields exist."""
    buyer = login_as("checkout-buyer@example.com")
    order = _make_order_for(buyer, approved_listing, db_session)

    # The checkout page collects no payment credentials (FSR-17)
    page = client.get(f"/orders/{order.id}")
    assert b"card" not in page.data.lower()
    assert b"cvv" not in page.data.lower()

    resp = client.post(f"/orders/{order.id}/checkout", follow_redirects=False)
    assert resp.status_code == 302

    db.session.refresh(order)
    assert order.payment_status == PaymentStatus.PAID or order.payment_status == "paid"
    assert (
        order.workflow_status == WorkflowStatus.SOLD or order.workflow_status == "sold"
    )
    assert AuditLog.query.filter_by(action_type="checkout_completed").first() is not None


def test_client_supplied_payment_status_ignored(client, login_as, approved_listing, db_session):
    """T-27: request tampering with payment fields changes nothing server-side."""
    buyer = login_as("tamper-buyer@example.com")
    order = _make_order_for(buyer, approved_listing, db_session)

    client.post(f"/orders/{order.id}/checkout", data={
        "payment_status": "refunded",     # ignored
        "committed_price": "0.01",        # ignored
        "workflow_status": "rejected",    # ignored
    })

    db.session.refresh(order)
    assert getattr(order.payment_status, "value", order.payment_status) == "paid"
    assert getattr(order.workflow_status, "value", order.workflow_status) == "sold"
    assert float(order.committed_price) == float(approved_listing.price)


def test_checkout_blocked_before_authentication(client, login_as, approved_listing, db_session):
    """T-28: checkout is impossible until the admin authenticates the item."""
    buyer = login_as("early-buyer@example.com")
    order = _make_order_for(buyer, approved_listing, db_session, workflow=WorkflowStatus.SHIPPED)

    resp = client.post(f"/orders/{order.id}/checkout")
    assert resp.status_code == 400

    db.session.refresh(order)
    assert getattr(order.payment_status, "value", order.payment_status) == "pending"


def test_checkout_forbidden_for_non_buyer(client, login_as, order, db_session):
    """Only the order's buyer can check out."""
    login_as("someone-else@example.com")
    order.workflow_status = WorkflowStatus.AUTHENTICATED
    db.session.commit()

    resp = client.post(f"/orders/{order.id}/checkout")
    assert resp.status_code == 403


def test_refund_is_admin_only(client, db_session, admin_user, buyer_user, approved_listing):
    """Payment paid -> refunded is an admin action; buyers/sellers cannot."""
    order = _make_order_for(buyer_user, approved_listing, db_session, workflow=WorkflowStatus.SOLD)
    order.payment_status = PaymentStatus.PAID
    db.session.commit()

    with pytest.raises(PermissionError):
        checkout_service.refund_order(order, buyer_user)

    checkout_service.refund_order(order, admin_user)
    assert getattr(order.payment_status, "value", order.payment_status) == "refunded"
    # refunded is terminal
    with pytest.raises(ValueError):
        checkout_service.refund_order(order, admin_user)
