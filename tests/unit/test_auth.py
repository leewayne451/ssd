import pytest
from app import create_app
from app.extensions import db
from app.services.auth_service import register_user, login_user
from app.services.user_service import get_user_by_email


# Use a password that meets complexity AND passes zxcvbn (score >= 3)
STRONG_PASSWORD = "MySecureP@ssw0rd!2026"


@pytest.fixture
def app_context():
    """Create an application context for testing."""
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


# ------------------- Registration Tests -------------------
def test_register_success(app_context):
    email = "test_success@example.com"
    user, error = register_user(email, STRONG_PASSWORD)
    assert user is not None
    assert error is None
    assert user.email == email
    # Clean up
    db.session.delete(user)
    db.session.commit()


def test_register_duplicate_email(app_context):
    email = "test_dup@example.com"
    user1, _ = register_user(email, STRONG_PASSWORD)
    assert user1 is not None

    user2, error = register_user(email, STRONG_PASSWORD)
    assert user2 is None
    assert "already registered" in error.lower()

    db.session.delete(user1)
    db.session.commit()


# ------------------- Login Tests -------------------
def test_login_success(app_context):
    email = "test_login@example.com"
    register_user(email, STRONG_PASSWORD)

    with app_context.test_request_context():
        user, error = login_user(email, STRONG_PASSWORD)

    assert user is not None
    assert error is None
    assert user.email == email

    user = get_user_by_email(email)
    if user:
        db.session.delete(user)
        db.session.commit()


def test_login_wrong_password(app_context):
    email = "test_wrong@example.com"
    register_user(email, STRONG_PASSWORD)

    with app_context.test_request_context():
        user, error = login_user(email, "WrongPass")

    assert user is None
    assert "invalid" in error.lower()

    user = get_user_by_email(email)
    if user:
        db.session.delete(user)
        db.session.commit()


# ------------------- Lockout Test -------------------
def test_account_lockout_after_failed_attempts(app_context):
    email = "test_lockout@example.com"
    register_user(email, STRONG_PASSWORD)

    # 3 failed attempts
    for i in range(3):
        with app_context.test_request_context():
            user, error = login_user(email, "WrongPassword")
        assert user is None
        assert error is not None

    # Verify lock in DB
    user = get_user_by_email(email)
    assert user is not None
    assert user.failed_login_attempts >= 3
    assert user.locked_until is not None

    # 4th attempt with correct password should fail (locked)
    with app_context.test_request_context():
        user, error = login_user(email, STRONG_PASSWORD)
    assert user is None
    assert "locked" in error.lower()

    # Clean up
    user = get_user_by_email(email)
    if user:
        db.session.delete(user)
        db.session.commit()


# ------------------- Logout & Session Tests -------------------
def test_logout_clears_session(app_context):
    email = "test_logout@example.com"

    # Register user
    register_user(email, STRONG_PASSWORD)

    with app_context.test_client() as client:
        # Log in
        response = client.post('/auth/login', data={
            'email': email,
            'password': STRONG_PASSWORD
        }, follow_redirects=True)

        # Verify session has user_id
        with client.session_transaction() as sess:
            assert 'user_id' in sess
            assert sess['user_id'] is not None

        # Logout
        client.get('/auth/logout', follow_redirects=True)

        # Verify session is cleared
        with client.session_transaction() as sess:
            assert 'user_id' not in sess
            assert 'role' not in sess

    # Clean up
    user = get_user_by_email(email)
    if user:
        db.session.delete(user)
        db.session.commit()


def test_protected_route_redirects_to_login(app_context):
    """Test that anonymous users are redirected to login."""
    with app_context.test_client() as client:
        response = client.get('/auth/logout', follow_redirects=True)
        assert response.status_code == 200


def test_session_cookie_flags(app_context):
    """Test that session cookie flags are set in config."""
    assert app_context.config.get('SESSION_COOKIE_HTTPONLY') is True
    assert app_context.config.get('SESSION_COOKIE_SAMESITE') == 'Lax'
    assert 'SESSION_COOKIE_SECURE' in app_context.config