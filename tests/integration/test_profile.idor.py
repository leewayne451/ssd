"""
Integration tests for Profile IDOR (M6).

Positive: User A can edit their own profile.
Negative/Abuse: User A cannot edit User B's profile (403).

Uses the real authentication flow (/auth/register, /auth/login) and
the real Profile routes (/profile/<id>/edit).

Fixtures from tests/conftest.py: client, db_session
"""

import re
import pytest
from flask import session

from app.models.user import User
from app.models.profile import Profile
from app.services.profile_service import create_profile


# ---------- Helper functions (no assumptions about fixtures) ----------

def register_user(client, email, password):
    """Register a user via the real /auth/register endpoint."""
    # First, get a CSRF token from the registration page
    resp = client.get("/auth/register")
    assert resp.status_code == 200
    token = _extract_csrf_token(resp.data)

    resp = client.post(
        "/auth/register",
        data={
            "email": email,
            "password": password,
            "confirm_password": password,
            "csrf_token": token,
        },
        follow_redirects=True,
    )
    # Registration should succeed
    assert b"Registration successful" in resp.data or b"registered" in resp.data.lower()
    return User.query.filter_by(email=email).first()


def login_user(client, email, password):
    """Log in a user via the real /auth/login endpoint."""
    # Get CSRF token from login page
    resp = client.get("/auth/login")
    assert resp.status_code == 200
    token = _extract_csrf_token(resp.data)

    resp = client.post(
        "/auth/login",
        data={
            "email": email,
            "password": password,
            "csrf_token": token,
        },
        follow_redirects=True,
    )
    # Login should succeed
    assert b"logged in" in resp.data.lower() or b"welcome" in resp.data.lower()
    return User.query.filter_by(email=email).first()


def _extract_csrf_token(html_bytes):
    """Extract csrf_token value from rendered HTML form."""
    match = re.search(rb'name="csrf_token" value="([^"]+)"', html_bytes)
    if not match:
        # If no token found, try a different pattern (some forms use hidden field)
        match = re.search(rb'id="csrf_token"[^>]+value="([^"]+)"', html_bytes)
    assert match, "Could not find CSRF token in HTML"
    return match.group(1).decode()


def create_user_directly(db_session, email, password_hash=None):
    """
    Bypass registration to create a user directly in the database.
    Useful for setting up test data quickly without going through the
    registration flow.
    """
    from werkzeug.security import generate_password_hash

    if password_hash is None:
        password_hash = generate_password_hash("testpass123")

    user = User(
        email=email,
        password_hash=password_hash,
        role="buyer",
        status="active",
        email_confirmed=True,
    )
    db_session.add(user)
    db_session.flush()  # Get the ID without committing

    # Create profile for the user
    profile = Profile(
        user_id=user.id,
        first_name="Test",
        last_name="User",
    )
    db_session.add(profile)
    db_session.commit()

    return user


def get_csrf_token_from_authenticated_page(client, url):
    """Visit a page that contains a form and extract the CSRF token."""
    resp = client.get(url)
    assert resp.status_code == 200
    return _extract_csrf_token(resp.data)


# ---------- Tests ----------

class TestProfileIDOR:
    """Test that users can only edit their own profiles."""

    def test_user_can_edit_own_profile(self, client, db_session):
        """
        Positive test: User A edits their own profile via the real
        edit endpoint. Should succeed with a 200 and a success flash.
        """
        # Arrange: Create and log in User A
        user_a = create_user_directly(db_session, "alice@test.com")
        profile_a = Profile.query.filter_by(user_id=user_a.id).first()

        # Log in User A via the real login flow
        resp = client.get("/auth/login")
        token = _extract_csrf_token(resp.data)

        resp = client.post(
            "/auth/login",
            data={
                "email": "alice@test.com",
                "password": "testpass123",
                "csrf_token": token,
            },
            follow_redirects=True,
        )
        assert b"logged in" in resp.data.lower() or b"welcome" in resp.data.lower()

        # Get a CSRF token from the profile edit page
        resp = client.get(f"/profile/{user_a.id}/edit")
        assert resp.status_code == 200
        edit_token = _extract_csrf_token(resp.data)

        # Act: Edit the profile
        resp = client.post(
            f"/profile/{user_a.id}/edit",
            data={
                "first_name": "Alice",
                "last_name": "Wonderland",
                "bio": "This is my bio with <script>alert('xss')</script>",
                "csrf_token": edit_token,
            },
            follow_redirects=True,
        )

        # Assert: Success flash and updated profile
        assert b"Profile updated successfully" in resp.data
        db_session.refresh(profile_a)
        assert profile_a.first_name == "Alice"
        assert profile_a.last_name == "Wonderland"
        # Bio should have HTML tags stripped
        assert "<script>" not in profile_a.bio
        assert "alert('xss')" not in profile_a.bio
        assert "This is my bio with" in profile_a.bio

    def test_user_cannot_edit_other_profile(self, client, db_session):
        """
        Negative/IDOR test: User A cannot edit User B's profile.
        Should return 403 Forbidden.
        """
        # Arrange: Create two users
        user_a = create_user_directly(db_session, "alice@test.com")
        user_b = create_user_directly(db_session, "bob@test.com")

        # Give User B some unique profile data
        profile_b = Profile.query.filter_by(user_id=user_b.id).first()
        profile_b.first_name = "Bob"
        profile_b.last_name = "Builder"
        db_session.commit()

        # Log in as User A
        resp = client.get("/auth/login")
        token = _extract_csrf_token(resp.data)

        resp = client.post(
            "/auth/login",
            data={
                "email": "alice@test.com",
                "password": "testpass123",
                "csrf_token": token,
            },
            follow_redirects=True,
        )
        assert b"logged in" in resp.data.lower() or b"welcome" in resp.data.lower()

        # Get a CSRF token from User A's own edit page (valid for their session)
        resp = client.get(f"/profile/{user_a.id}/edit")
        assert resp.status_code == 200
        edit_token = _extract_csrf_token(resp.data)

        # Act: Attempt to edit User B's profile
        resp = client.post(
            f"/profile/{user_b.id}/edit",
            data={
                "first_name": "Hacked",
                "last_name": "Account",
                "bio": "This should not work",
                "csrf_token": edit_token,
            },
            follow_redirects=False,  # Don't follow redirects to see the raw status
        )

        # Assert: 403 Forbidden (from assert_owner in ownership.py)
        assert resp.status_code == 403

        # Verify User B's profile was NOT changed
        db_session.refresh(profile_b)
        assert profile_b.first_name == "Bob"
        assert profile_b.last_name == "Builder"

    def test_unauthenticated_user_cannot_edit_profile(self, client, db_session):
        """
        Negative test: Anonymous user cannot edit any profile.
        Should be redirected to login (302) or get 401.
        """
        # Arrange: Create a user but DO NOT log in
        user = create_user_directly(db_session, "charlie@test.com")

        # Act: Try to edit the profile without logging in
        resp = client.get(f"/profile/{user.id}/edit")
        # Since login_required is used, should redirect to login or 401
        # Flask's login_required typically returns 401 by default
        assert resp.status_code in (302, 401)

        # Try POST as well
        resp = client.post(
            f"/profile/{user.id}/edit",
            data={
                "first_name": "Anonymous",
                "last_name": "Hacker",
            },
            follow_redirects=False,
        )
        assert resp.status_code in (302, 401)

    def test_non_existent_profile_returns_404(self, client, db_session):
        """
        Edge case: Requesting a profile that does not exist.
        """
        # Arrange: Log in a user
        user = create_user_directly(db_session, "diana@test.com")

        resp = client.get("/auth/login")
        token = _extract_csrf_token(resp.data)
        client.post(
            "/auth/login",
            data={
                "email": "diana@test.com",
                "password": "testpass123",
                "csrf_token": token,
            },
            follow_redirects=True,
        )

        # Act: Request a non-existent profile
        non_existent_id = 99999
        resp = client.get(f"/profile/{non_existent_id}")
        assert resp.status_code == 404

        resp = client.get(f"/profile/{non_existent_id}/edit")
        assert resp.status_code == 404