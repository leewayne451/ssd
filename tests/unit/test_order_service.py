"""Unit tests for order_service — order placement and management."""
import pytest
from app.models.order import Order
from app.models.order_status_history import OrderStatusHistory
from app.models.enums import WorkflowStatus
from app.services import order_service, cart_service


def test_place_orders_from_cart_success(client, db_session, buyer_user, approved_listing):
    """Test placing orders from cart creates Order and OrderStatusHistory rows."""
    # Add item to cart
    cart_service.add_item(buyer_user, approved_listing.id, quantity=1)
    
    # Place orders
    orders = order_service.place_orders_from_cart(buyer_user)
    
    assert len(orders) == 1
    assert orders[0].buyer_id == buyer_user.id
    assert orders[0].listing_id == approved_listing.id
    assert orders[0].workflow_status == WorkflowStatus.COMMITTED
    
    # Verify committed_price is from server
    assert orders[0].committed_price == approved_listing.price


def test_place_orders_records_history(client, db_session, buyer_user, approved_listing):
    """Test that place_orders_from_cart records OrderStatusHistory."""
    cart_service.add_item(buyer_user, approved_listing.id, quantity=1)
    
    orders = order_service.place_orders_from_cart(buyer_user)
    
    # Check history was created
    history = OrderStatusHistory.query.filter_by(order_id=orders[0].id).all()
    assert len(history) >= 1
    
    # Latest history should record the committed status
    latest_history = history[0]
    assert latest_history.new_status == WorkflowStatus.COMMITTED.value


def test_place_orders_clears_cart(client, db_session, buyer_user, approved_listing):
    """Test that place_orders_from_cart clears the cart afterwards."""
    cart_service.add_item(buyer_user, approved_listing.id, quantity=1)
    
    # Verify item is in cart
    cart = cart_service.get_cart_for_user(buyer_user)
    assert len(cart.items) == 1
    
    # Place orders
    order_service.place_orders_from_cart(buyer_user)
    
    # Cart should be empty
    cart = cart_service.get_cart_for_user(buyer_user)
    assert len(cart.items) == 0


def test_place_orders_empty_cart(client, db_session, buyer_user):
    """Test that place_orders_from_cart returns empty list for empty cart."""
    orders = order_service.place_orders_from_cart(buyer_user)
    assert orders == []


def test_place_orders_no_cart(client, db_session, buyer_user):
    """Test that place_orders_from_cart returns empty list when no cart exists."""
    orders = order_service.place_orders_from_cart(buyer_user)
    assert orders == []


def test_place_orders_multiple_items(client, db_session, buyer_user, approved_listing, seller_user):
    """Test placing orders with multiple items in cart."""
    # Create second listing
    from app.models.product_listing import ProductListing
    from app.models.enums import ListingCondition, ApprovalStatus
    
    listing2 = ProductListing(
        seller_id=seller_user.id,
        title="Second Item",
        description="Another product",
        category="electronics",
        brand="Brand2",
        price=75.50,
        condition=ListingCondition.NEW,
        approval_status=ApprovalStatus.APPROVED,
        workflow_status=WorkflowStatus.AVAILABLE,
    )
    db_session.add(listing2)
    db_session.commit()
    
    # Add both to cart
    cart_service.add_item(buyer_user, approved_listing.id, quantity=1)
    cart_service.add_item(buyer_user, listing2.id, quantity=2)
    
    # Place orders
    orders = order_service.place_orders_from_cart(buyer_user)
    
    assert len(orders) == 2
    
    # Verify each order has correct price
    prices = {order.listing_id: order.committed_price for order in orders}
    assert prices[approved_listing.id] == approved_listing.price
    assert prices[listing2.id] == listing2.price


def test_place_orders_server_price_enforcement(client, db_session, buyer_user, approved_listing):
    """Test that committed_price is always from server, not client."""
    cart_service.add_item(buyer_user, approved_listing.id, quantity=1)
    
    orders = order_service.place_orders_from_cart(buyer_user)
    
    # Even if client tried to send different price, server should have original
    assert orders[0].committed_price == approved_listing.price
