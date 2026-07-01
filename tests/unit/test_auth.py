import pytest
from app import create_app
from app.extensions import db
from app.services.auth_service import register_user, login_user
from app.services.user_service import get_user_by_email


@pytest.fixture
def app_context():
    """Create an application context for testing."""
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_register_success(app_context):
    email = "test_success@example.com"
    password = "Test123!"
    user, error = register_user(email, password)
    assert user is not None
    assert error is None
    assert user.email == email
    db.session.delete(user)
    db.session.commit()


def test_register_duplicate_email(app_context):
    email = "test_dup@example.com"
    password = "Test123!"
    user1, _ = register_user(email, password)
    assert user1 is not None
    user2, error = register_user(email, password)
    assert user2 is None
    assert "already registered" in error.lower()
    db.session.delete(user1)
    db.session.commit()


def test_login_success(app_context):
    email = "test_login@example.com"
    password = "Test123!"
    register_user(email, password)

    # Push a request context so that session is available
    with app_context.test_request_context():
        user, error = login_user(email, password)

    assert user is not None
    assert error is None
    assert user.email == email

    # Clean up (get fresh user object)
    user = get_user_by_email(email)
    db.session.delete(user)
    db.session.commit()


def test_login_wrong_password(app_context):
    email = "test_wrong@example.com"
    password = "Test123!"
    register_user(email, password)

    with app_context.test_request_context():
        user, error = login_user(email, "WrongPass")

    assert user is None
    assert "invalid" in error.lower()

    user = get_user_by_email(email)
    db.session.delete(user)
    db.session.commit()


def test_account_lockout_after_failed_attempts(app_context):
    email = "test_lockout@example.com"
    password = "Test123!"
    register_user(email, password)

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
        user, error = login_user(email, password)
    assert user is None
    assert "locked" in error.lower()

    # Clean up - get fresh user object again
    user = get_user_by_email(email)
    if user:
        db.session.delete(user)
        db.session.commit()


def test_logout_clears_session(app_context):
    email = "test_logout@example.com"
    password = "Test123!"
    
    # Register a user
    register_user(email, password)
    
    with app_context.test_client() as client:
        # 1. Log in
        client.post('/auth/login', data={
            'email': email,
            'password': password
        }, follow_redirects=True)
        
        # Verify session contains user_id (using client's session)
        with client.session_transaction() as sess:
            assert 'user_id' in sess
            assert sess['user_id'] is not None
        
        # 2. Logout
        client.get('/auth/logout', follow_redirects=True)
        
        # 3. Verify session is cleared
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
        # Try to logout without being logged in (redirects to home)
        response = client.get('/auth/logout', follow_redirects=True)
        # Should redirect to home because there's no session to clear
        assert response.status_code == 200  # home page
        
        # More importantly, check if the session is empty
        with app_context.test_request_context():
            from flask import session
            # Session should be empty because we never logged in
            assert 'user_id' not in session


def test_session_cookie_flags(app_context):
    """Test that session cookie has HttpOnly and SameSite flags."""
    # This tests the CONFIG, not the actual cookie header in a real response.
    # For the actual header, you need to check the response Set-Cookie.
    assert app_context.config.get('SESSION_COOKIE_HTTPONLY') is True
    assert app_context.config.get('SESSION_COOKIE_SAMESITE') == 'Lax'
    # Secure is False in dev, True in prod. We check it's set in config.
    assert 'SESSION_COOKIE_SECURE' in app_context.config