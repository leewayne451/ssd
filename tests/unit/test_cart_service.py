"""Unit tests for cart_service — shopping cart operations."""
import pytest
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.product_listing import ProductListing
from app.models.enums import WorkflowStatus
from app.services import cart_service


def test_get_or_create_cart_creates_cart(client, db_session, buyer_user):
    """Test that get_or_create_cart creates a new cart if one doesn't exist."""
    cart = cart_service.get_or_create_cart(buyer_user)
    assert cart is not None
    assert cart.buyer_id == buyer_user.id
    
    # Verify it's in the database
    found = Cart.query.filter_by(buyer_id=buyer_user.id).first()
    assert found is not None
    assert found.id == cart.id


def test_get_or_create_cart_returns_existing(client, db_session, buyer_user):
    """Test that get_or_create_cart returns existing cart on second call."""
    cart1 = cart_service.get_or_create_cart(buyer_user)
    cart2 = cart_service.get_or_create_cart(buyer_user)
    assert cart1.id == cart2.id


def test_get_cart_for_user_returns_none_when_not_exists(client, db_session, buyer_user):
    """Test that get_cart_for_user returns None when cart doesn't exist."""
    cart = cart_service.get_cart_for_user(buyer_user)
    assert cart is None


def test_get_cart_for_user_returns_existing_cart(client, db_session, buyer_user):
    """Test that get_cart_for_user returns existing cart."""
    created_cart = cart_service.get_or_create_cart(buyer_user)
    found_cart = cart_service.get_cart_for_user(buyer_user)
    assert found_cart is not None
    assert found_cart.id == created_cart.id


def test_add_item_to_cart_success(client, db_session, buyer_user, approved_listing):
    """Test adding an item to cart."""
    item = cart_service.add_item(buyer_user, approved_listing.id, quantity=2)
    
    assert item is not None
    assert item.listing_id == approved_listing.id
    assert item.quantity == 2
    
    # Verify it's in the database
    found = CartItem.query.get(item.id)
    assert found is not None
    assert found.quantity == 2


def test_add_item_validates_quantity(client, db_session, buyer_user, approved_listing):
    """Test that add_item rejects invalid quantities."""
    with pytest.raises(ValueError, match="Quantity must be > 0"):
        cart_service.add_item(buyer_user, approved_listing.id, quantity=0)
    
    with pytest.raises(ValueError, match="Quantity must be > 0"):
        cart_service.add_item(buyer_user, approved_listing.id, quantity=-1)


def test_add_item_validates_listing_exists(client, db_session, buyer_user):
    """Test that add_item rejects non-existent listings."""
    with pytest.raises(ValueError, match="Listing not found"):
        cart_service.add_item(buyer_user, 99999, quantity=1)


def test_add_item_updates_existing_quantity(client, db_session, buyer_user, approved_listing):
    """Test that adding the same item updates quantity instead of duplicating."""
    item1 = cart_service.add_item(buyer_user, approved_listing.id, quantity=1)
    item2 = cart_service.add_item(buyer_user, approved_listing.id, quantity=3)
    
    # Should be the same item with updated quantity
    assert item1.id == item2.id
    assert item2.quantity == 3
    
    # Only one CartItem should exist
    cart = cart_service.get_cart_for_user(buyer_user)
    assert len(cart.items) == 1


def test_remove_item_success(client, db_session, buyer_user, approved_listing):
    """Test removing an item from cart."""
    cart_service.add_item(buyer_user, approved_listing.id, quantity=1)
    
    removed = cart_service.remove_item(buyer_user, approved_listing.id)
    assert removed is True
    
    # Verify it's gone
    cart = cart_service.get_cart_for_user(buyer_user)
    assert len(cart.items) == 0


def test_remove_item_not_found(client, db_session, buyer_user):
    """Test that remove_item returns False when item not in cart."""
    cart_service.get_or_create_cart(buyer_user)
    
    removed = cart_service.remove_item(buyer_user, 99999)
    assert removed is False


def test_remove_item_no_cart(client, db_session, buyer_user):
    """Test that remove_item returns False when user has no cart."""
    removed = cart_service.remove_item(buyer_user, 99999)
    assert removed is False


def test_update_item_quantity_success(client, db_session, buyer_user, approved_listing):
    """Test updating item quantity."""
    cart_service.add_item(buyer_user, approved_listing.id, quantity=1)
    
    updated = cart_service.update_item_quantity(buyer_user, approved_listing.id, quantity=5)
    assert updated is True
    
    item = CartItem.query.filter_by(listing_id=approved_listing.id).first()
    assert item.quantity == 5


def test_update_item_quantity_validates(client, db_session, buyer_user, approved_listing):
    """Test that update_item_quantity validates quantity."""
    cart_service.add_item(buyer_user, approved_listing.id, quantity=1)
    
    with pytest.raises(ValueError, match="Quantity must be > 0"):
        cart_service.update_item_quantity(buyer_user, approved_listing.id, quantity=0)


def test_update_item_quantity_not_found(client, db_session, buyer_user):
    """Test that update_item_quantity returns False when item not found."""
    cart_service.get_or_create_cart(buyer_user)
    
    updated = cart_service.update_item_quantity(buyer_user, 99999, quantity=1)
    assert updated is False


def test_clear_cart_success(client, db_session, buyer_user, approved_listing, seller_user):
    """Test clearing all items from cart."""
    from app.models.product_listing import ProductListing
    from app.models.enums import ListingCondition, ApprovalStatus
    
    # Create second listing
    listing2 = ProductListing(
        seller_id=seller_user.id,
        title="Test Item 2",
        description="Another product",
        category="electronics",
        brand="Brand2",
        price=50.00,
        condition=ListingCondition.NEW,
        approval_status=ApprovalStatus.APPROVED,
        workflow_status=WorkflowStatus.AVAILABLE,
    )
    db_session.add(listing2)
    db_session.flush()
    
    # Add both items to cart
    cart_service.add_item(buyer_user, approved_listing.id, quantity=1)
    cart_service.add_item(buyer_user, listing2.id, quantity=1)
    
    cleared = cart_service.clear_cart(buyer_user)
    assert cleared is True
    
    cart = cart_service.get_cart_for_user(buyer_user)
    assert len(cart.items) == 0


def test_clear_cart_empty(client, db_session, buyer_user):
    """Test that clear_cart returns False when cart is empty."""
    cart_service.get_or_create_cart(buyer_user)
    
    cleared = cart_service.clear_cart(buyer_user)
    assert cleared is False


def test_get_cart_total_calculates_correctly(client, db_session, buyer_user, approved_listing):
    """Test that get_cart_total calculates total using server prices."""
    cart_service.add_item(buyer_user, approved_listing.id, quantity=2)
    
    total = cart_service.get_cart_total(buyer_user)
    expected = float(approved_listing.price) * 2
    assert total == expected


def test_get_cart_total_empty_cart(client, db_session, buyer_user):
    """Test that get_cart_total returns 0 for empty cart."""
    total = cart_service.get_cart_total(buyer_user)
    assert total == 0.0


def test_get_cart_total_no_cart(client, db_session, buyer_user):
    """Test that get_cart_total returns 0 when user has no cart."""
    total = cart_service.get_cart_total(buyer_user)
    assert total == 0.0
