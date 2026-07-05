"""Unit tests for workflow_service — order workflow state machine."""
import pytest
from app.models.order import Order
from app.models.order_status_history import OrderStatusHistory
from app.models.enums import WorkflowStatus, UserRole
from app.services import workflow_service


def test_can_transition_valid_path(client, db_session):
    """The D1 H-3 chain: committed -> ... -> authenticated -> sold."""
    assert workflow_service.can_transition("committed", "awaiting_shipment") is True
    assert workflow_service.can_transition("awaiting_shipment", "shipped") is True
    assert workflow_service.can_transition("shipped", "under_authentication") is True
    assert workflow_service.can_transition("under_authentication", "authenticated") is True
    assert workflow_service.can_transition("authenticated", "sold") is True


def test_can_transition_invalid_path(client, db_session):
    """Test that can_transition rejects invalid state transitions."""
    assert workflow_service.can_transition("committed", "sold") is False
    assert workflow_service.can_transition("shipped", "awaiting_shipment") is False
    assert workflow_service.can_transition("rejected", "committed") is False
    # the core D1 rule: an order can NEVER complete without authentication
    assert workflow_service.can_transition("shipped", "sold") is False


def test_can_transition_terminal_state(client, db_session):
    """Test that terminal states cannot transition."""
    assert workflow_service.can_transition("sold", "shipped") is False
    assert workflow_service.can_transition("rejected", "committed") is False
    assert workflow_service.can_transition("authenticated", "shipped") is False


def test_is_actor_allowed_admin_always_allowed(client, db_session, admin_user):
    """Test that admin can make any allowed transition."""
    assert workflow_service.is_actor_allowed("committed", "awaiting_shipment", admin_user) is True
    assert workflow_service.is_actor_allowed("awaiting_shipment", "shipped", admin_user) is True
    assert workflow_service.is_actor_allowed("shipped", "under_authentication", admin_user) is True
    assert workflow_service.is_actor_allowed("under_authentication", "authenticated", admin_user) is True


def test_is_actor_allowed_seller_restricted(client, db_session, seller_user):
    """Test that seller can only make certain transitions."""
    assert workflow_service.is_actor_allowed("committed", "awaiting_shipment", seller_user) is True
    assert workflow_service.is_actor_allowed("awaiting_shipment", "shipped", seller_user) is True
    # Sellers can never move an item into/through authentication or completion
    assert workflow_service.is_actor_allowed("shipped", "under_authentication", seller_user) is False
    assert workflow_service.is_actor_allowed("under_authentication", "authenticated", seller_user) is False
    assert workflow_service.is_actor_allowed("authenticated", "sold", seller_user) is False


def test_is_actor_allowed_buyer_not_allowed(client, db_session, buyer_user):
    """Test that buyer cannot make transitions."""
    assert workflow_service.is_actor_allowed("committed", "awaiting_shipment", buyer_user) is False


def test_is_actor_allowed_none_user(client, db_session):
    """Test that None user is not allowed."""
    assert workflow_service.is_actor_allowed("committed", "awaiting_shipment", None) is False


def test_transition_order_success(client, db_session, seller_user, order):
    """Test successful order transition."""
    order = workflow_service.transition_order(order, "awaiting_shipment", seller_user)
    
    assert order.workflow_status == "awaiting_shipment"
    
    # Verify history was recorded
    history = OrderStatusHistory.query.filter_by(order_id=order.id).first()
    assert history is not None
    assert history.new_status == "awaiting_shipment"


def test_transition_order_illegal_transition(client, db_session, seller_user, order):
    """Test that illegal transitions are rejected."""
    with pytest.raises(ValueError, match="illegal workflow transition"):
        workflow_service.transition_order(order, "sold", seller_user)


def test_transition_order_unauthorized_actor(client, db_session, buyer_user, order):
    """Test that unauthorized actors are rejected."""
    with pytest.raises(PermissionError, match="not authorized"):
        workflow_service.transition_order(order, "awaiting_shipment", buyer_user)


def test_transition_order_records_history(client, db_session, admin_user, order):
    """Test that transitions record OrderStatusHistory with actor info."""
    old_status = order.workflow_status
    order = workflow_service.transition_order(order, "awaiting_shipment", admin_user)
    
    history = OrderStatusHistory.query.filter_by(order_id=order.id).first()
    assert history.actor_user_id == admin_user.id
    assert history.old_status == "committed"
    assert history.new_status == "awaiting_shipment"


def test_transition_order_multi_step(client, db_session, seller_user, admin_user, buyer_user, order):
    """The complete D1 H-3 sequence: commit -> ship -> authenticate -> sold."""
    # Seller accepts: committed -> awaiting_shipment
    order = workflow_service.transition_order(order, "awaiting_shipment", seller_user)
    assert order.workflow_status == "awaiting_shipment"

    # Seller ships: awaiting_shipment -> shipped
    order = workflow_service.transition_order(order, "shipped", seller_user)
    assert order.workflow_status == "shipped"

    # Admin receives the item for in-house review: shipped -> under_authentication
    order = workflow_service.transition_order(order, "under_authentication", admin_user)
    assert order.workflow_status == "under_authentication"

    # Admin authenticates: under_authentication -> authenticated
    order = workflow_service.transition_order(order, "authenticated", admin_user)
    assert order.workflow_status == "authenticated"

    # Buyer completes: authenticated -> sold
    order = workflow_service.transition_order(order, "sold", buyer_user)
    assert order.workflow_status == "sold"

    # Verify history chain was created
    histories = OrderStatusHistory.query.filter_by(order_id=order.id).order_by(OrderStatusHistory.changed_at).all()
    assert len(histories) >= 5


def test_transition_order_rejection_path(client, db_session, admin_user, order):
    """Admins can reject an order for workflow compliance (H-3)."""
    order = workflow_service.transition_order(order, "rejected", admin_user)
    assert order.workflow_status == "rejected"

    # Rejected is terminal
    with pytest.raises(ValueError, match="illegal workflow transition"):
        workflow_service.transition_order(order, "awaiting_shipment", admin_user)


def test_seller_cannot_reject_orders(client, db_session, seller_user, order):
    """Rejection is an admin compliance action (H-3: Rejected actor = Admin)."""
    with pytest.raises(PermissionError, match="not authorized"):
        workflow_service.transition_order(order, "rejected", seller_user)


def test_transition_order_authentication_path(client, db_session, admin_user):
    """Test authentication workflow path."""
    from app.models.product_listing import ProductListing
    from app.models.enums import ListingCondition, ApprovalStatus
    
    # Create an order
    user = admin_user
    listing = ProductListing.query.first()
    if not listing:
        listing = ProductListing(
            seller_id=user.id,
            title="Test",
            description="Test",
            category="test",
            brand="test",
            price=100.0,
            condition=ListingCondition.NEW,
            approval_status=ApprovalStatus.APPROVED,
            workflow_status=WorkflowStatus.AVAILABLE,
        )
        from app.extensions import db
        db.session.add(listing)
        db.session.commit()
    
    order = Order(
        buyer_id=user.id,
        listing_id=listing.id,
        committed_price=100.0,
        workflow_status=WorkflowStatus.UNDER_AUTHENTICATION,
    )
    from app.extensions import db
    db.session.add(order)
    db.session.commit()
    
    # Admin can authenticate
    order = workflow_service.transition_order(order, "authenticated", admin_user)
    assert order.workflow_status == "authenticated"
