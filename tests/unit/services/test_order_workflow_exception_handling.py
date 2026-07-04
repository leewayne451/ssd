import pytest

from app.services.order_service import place_orders_from_cart
from app.services.workflow_service import transition_order
from app.models.product_listing import ProductListing
from app.models.order import Order
from app.models.enums import ApprovalStatus, ListingCondition, WorkflowStatus


def test_place_orders_from_cart_logs_audit_exception(app, db_session, buyer, caplog, monkeypatch):
    # Create listing so the order can be placed.
    listing = ProductListing(
        seller_id=buyer.id,
        title="Test Item",
        description="Test description",
        category="test",
        brand="test",
        price=100.00,
        condition=ListingCondition.NEW,
        approval_status=ApprovalStatus.APPROVED,
        workflow_status=WorkflowStatus.AVAILABLE,
    )
    db_session.add(listing)
    db_session.flush()

    # Add one cart item for buyer.
    from app.services.cart_service import add_item
    add_item(buyer, listing.id, 1)

    # Simulate audit failure by monkeypatching audit_record.
    import app.services.order_service as order_service_module

    def fail_audit(*args, **kwargs):
        return False

    monkeypatch.setattr(order_service_module, "audit_record", fail_audit)

    caplog.set_level("ERROR")
    orders = place_orders_from_cart(buyer)

    assert len(orders) == 1
    assert "Audit logging failed for order placement" in caplog.text


def test_transition_order_logs_audit_exception(app, db_session, buyer, admin_user, caplog, monkeypatch):
    listing = ProductListing(
        seller_id=buyer.id,
        title="Test Item",
        description="Test description",
        category="test",
        brand="test",
        price=100.00,
        condition="NEW",
        approval_status="APPROVED",
        workflow_status="AVAILABLE",
    )
    db_session.add(listing)
    db_session.flush()

    # Create an order and commit it so it has an ID.
    order = Order(
        buyer_id=buyer.id,
        listing_id=listing.id,
        committed_price=listing.price,
        workflow_status=WorkflowStatus.COMMITTED,
    )
    db_session.add(order)
    db_session.commit()

    # Force audit failure during workflow transition.
    import app.services.workflow_service as workflow_service_module

    def fail_audit(*args, **kwargs):
        return False

    monkeypatch.setattr(workflow_service_module, "audit_record", fail_audit)

    caplog.set_level("ERROR")
    updated_order = transition_order(order, "awaiting_shipment", admin_user)

    assert updated_order.workflow_status == "awaiting_shipment"
    assert "Audit logging failed for workflow transition" in caplog.text
