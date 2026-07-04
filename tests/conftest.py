"""
Chateau Collective -- Pytest fixtures

Provides:
  - app           : session-scoped Flask app in testing mode
  - client        : function-scoped, fresh Flask test client
  - db_session    : function-scoped SQLAlchemy session, clean schema per test
  - make_user     : factory for creating User rows in the test DB
  - buyer         : pre-built buyer User
  - seller_user   : pre-built seller User
  - admin_user    : pre-built admin User
  - auth_client   : test client with a logged-in buyer session

Usage for teammates (Phase 1+):
    def test_something(buyer, db_session, client):
        assert buyer.role.value == "buyer"

    def test_protected(auth_client):
        resp = auth_client.get("/profile")
        assert resp.status_code == 200
"""

import os
import sys
import pytest

# Ensure the project root (ssd/) is on sys.path so top-level imports like
# `from app import create_app` work when running pytest from the project
# or workspace root.
root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root not in sys.path:
    sys.path.insert(0, root)

from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db as _db
from app.models.user import User
from app.models.enums import UserRole


# ---------------------------------------------------------------------------
# App + DB setup
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def app():
    """
    Create a Flask application configured for the test suite.
    Session-scoped: created once, torn down after the full test run.
    """
    flask_app = create_app("testing")

    ctx = flask_app.app_context()
    ctx.push()

    _db.create_all()

    yield flask_app

    _db.drop_all()
    ctx.pop()


@pytest.fixture()
def client(app):
    """Flask test client -- fresh per test (clean cookie jar)."""
    return app.test_client()


@pytest.fixture()
def db_session(app):
    """
    Function-scoped session that guarantees a clean, empty schema per test.

    Drops and recreates all tables before each test, so every test starts
    from an empty database. Crucially this survives a commit() made by the
    code under test (e.g. audit_service.record) -- unlike a SAVEPOINT, which
    an inner commit() invalidates. In-memory SQLite makes drop/create cheap.

    Downstream fixtures (make_user, buyer, etc.) build their rows on this
    clean slate.
    """
    _db.session.remove()      # close any leftover session/transaction
    _db.drop_all()
    _db.create_all()

    yield _db.session

    _db.session.remove()      # discard uncommitted work; reset for next test


# ---------------------------------------------------------------------------
# User factory and role fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def make_user(db_session):
    """
    Factory function: creates a User row in the test DB.

        user = make_user("alice@test.local", role=UserRole.SELLER)

    The row is flushed (PK assigned) but not committed; it rolls back
    automatically when db_session teardown runs.
    """
    def _factory(email, password="Test1234!", role=UserRole.BUYER):
        user = User(
            email=email,
            password_hash=generate_password_hash(password),
            role=role,
        )
        db_session.add(user)
        db_session.flush()  # get PK without committing
        return user

    return _factory


@pytest.fixture()
def buyer(make_user):
    """A ready-to-use buyer User (role=BUYER)."""
    return make_user("buyer@test.local", role=UserRole.BUYER)


@pytest.fixture()
def seller_user(make_user):
    """A ready-to-use seller User (role=SELLER)."""
    return make_user("seller@test.local", role=UserRole.SELLER)


@pytest.fixture()
def admin_user(make_user):
    """A ready-to-use admin User (role=ADMIN)."""
    return make_user("admin@test.local", role=UserRole.ADMIN)


# ---------------------------------------------------------------------------
# Authenticated test client
# ---------------------------------------------------------------------------

@pytest.fixture()
def buyer_user(buyer):
    """Alias for buyer fixture — for M4 consistency."""
    return buyer


@pytest.fixture()
def auth_client(client, buyer):
    """
    Test client with an active buyer session.

    Sets session keys directly -- no HTTP login round-trip required.
    Key names (user_id, user_role) must match what M1 writes on login.
    Update them here once auth_routes.py finalises the session contract.
    """
    with client.session_transaction() as sess:
        sess["user_id"] = buyer.id
        sess["user_role"] = buyer.role.value
    return client


# ---------------------------------------------------------------------------
# M4 Cart & Order fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def approved_listing(seller_user, db_session):
    """A ready-to-use approved product listing."""
    from app.models.product_listing import ProductListing
    from app.models.enums import ListingCondition, ApprovalStatus

    listing = ProductListing(
        seller_id=seller_user.id,
        title="Test Product",
        description="A test product for cart and order tests",
        category="electronics",
        brand="TestBrand",
        price=99.99,
        condition=ListingCondition.NEW,
        approval_status=ApprovalStatus.APPROVED,
    )
    db_session.add(listing)
    db_session.flush()
    return listing


@pytest.fixture()
def order(buyer_user, approved_listing, db_session):
    """A ready-to-use order for workflow testing."""
    from app.models.order import Order
    from app.models.enums import WorkflowStatus

    order = Order(
        buyer_id=buyer_user.id,
        listing_id=approved_listing.id,
        committed_price=approved_listing.price,
        workflow_status=WorkflowStatus.COMMITTED,
    )
    db_session.add(order)
    db_session.flush()
    return order
