# cart_service — business logic layer.
from typing import Optional

from app.extensions import db
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.product_listing import ProductListing


def get_or_create_cart(user):
    """Get or create a cart for the user."""
    cart = Cart.query.filter_by(buyer_id=user.id).first()
    if not cart:
        cart = Cart(buyer_id=user.id)
        db.session.add(cart)
        db.session.commit()
    return cart


def get_cart_for_user(user):
    """Get user's cart, or None if doesn't exist."""
    return Cart.query.filter_by(buyer_id=user.id).first()


def add_item(user, listing_id: int, quantity: int = 1) -> Optional[CartItem]:
    """
    Add item to cart. Returns CartItem on success, None on failure.
    - Validates listing exists
    - Validates quantity > 0
    - Server-side validation: no client-trusted quantity
    """
    if quantity <= 0:
        raise ValueError("Quantity must be > 0")
    
    # Verify listing exists
    listing = ProductListing.query.get(listing_id)
    if not listing:
        raise ValueError("Listing not found")

    # SFR-09: only approved, active, still-AVAILABLE items may enter a cart —
    # an item committed to another buyer (or sold) is out of play.
    approval = getattr(listing.approval_status, "value", listing.approval_status)
    item_state = getattr(listing.workflow_status, "value", listing.workflow_status)
    if approval != "approved" or not listing.is_active or item_state != "available":
        raise ValueError("Listing is not available")

    cart = get_or_create_cart(user)
    
    # Check if item already in cart; if so, update quantity
    existing = CartItem.query.filter_by(
        cart_id=cart.id, listing_id=listing_id
    ).first()
    
    if existing:
        existing.quantity = quantity
        db.session.add(existing)
    else:
        item = CartItem(cart_id=cart.id, listing_id=listing_id, quantity=quantity)
        db.session.add(item)
    
    db.session.commit()
    return existing or item


def remove_item(user, listing_id: int) -> bool:
    """Remove item from user's cart. Returns True if removed, False if not found."""
    cart = get_cart_for_user(user)
    if not cart:
        return False
    
    item = CartItem.query.filter_by(
        cart_id=cart.id, listing_id=listing_id
    ).first()
    
    if not item:
        return False
    
    db.session.delete(item)
    db.session.commit()
    return True


def update_item_quantity(user, listing_id: int, quantity: int) -> bool:
    """
    Update quantity of item in cart.
    - Server-side validation: quantity must be > 0
    - Returns True on success, False if item not found
    """
    if quantity <= 0:
        raise ValueError("Quantity must be > 0")
    
    cart = get_cart_for_user(user)
    if not cart:
        return False
    
    item = CartItem.query.filter_by(
        cart_id=cart.id, listing_id=listing_id
    ).first()
    
    if not item:
        return False
    
    item.quantity = quantity
    db.session.add(item)
    db.session.commit()
    return True


def clear_cart(user) -> bool:
    """Clear all items from user's cart. Returns True if any items were removed."""
    cart = get_cart_for_user(user)
    if not cart or not cart.items:
        return False
    
    for item in cart.items:
        db.session.delete(item)
    db.session.commit()
    return True


def get_cart_total(user) -> float:
    """Calculate cart total using server-side listing prices."""
    cart = get_cart_for_user(user)
    if not cart:
        return 0.0
    
    total = 0.0
    for item in cart.items:
        listing = ProductListing.query.get(item.listing_id)
        if listing:
            total += float(listing.price) * item.quantity
    return total
