"""
Integration tests for Profile IDOR (M6, sub-issue 6.4).

Positive: a user can edit their own profile.
Negative/Abuse: a user cannot edit another user's profile (403, from
                assert_owner in app/security/ownership.py).

These tests are self-contained: they build a fresh in-memory app + database
per test (so there is no cross-test state leakage) and authenticate by
seeding the session directly, rather than depending on the auth login HTML
or the shared db_session fixture. CSRF is disabled in TestingConfig, so no
token handling is required here (CSRF enforcement is covered separately in
tests/security/test_csrf.py).
"""

import pytest

from app import create_app
from app.extensions import db as _db
from app.models.user import User
from app.models.profile import Profile


# ----------------------------- fixtures --------------------------------

@pytest.fixture
def app():
    """A fresh application + schema for each test (full isolation)."""
    application = create_app("testing")
    with application.app_context():
        _db.create_all()
        try:
            yield application
        finally:
            _db.session.remove()
            _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


# ----------------------------- helpers ---------------------------------

def create_user_with_profile(email, first="Test", last="User"):
    """Create a user and their profile directly in the database."""
    from werkzeug.security import generate_password_hash

    user = User(
        email=email,
        password_hash=generate_password_hash("testpass123"),
        role="buyer",
        status="active",
        email_confirmed=True,
    )
    _db.session.add(user)
    _db.session.flush()  # assign user.id

    profile = Profile(user_id=user.id, first_name=first, last_name=last)
    _db.session.add(profile)
    _db.session.commit()
    return user


def login_as(client, user):
    """Authenticate the test client by seeding the session (no login route)."""
    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["role"] = "buyer"


# ------------------------------ tests ----------------------------------

class TestProfileIDOR:
    """A user may only edit their own profile."""

    def test_user_can_edit_own_profile(self, client):
        """Positive: user edits their own profile -> success + persisted."""
        user_a = create_user_with_profile("alice@test.com")
        login_as(client, user_a)

        resp = client.post(
            f"/profile/{user_a.id}/edit",
            data={
                "first_name": "Alice",
                "last_name": "Wonderland",
                "bio": "This is my bio with <script>alert('xss')</script>",
            },
            follow_redirects=True,
        )

        assert resp.status_code == 200
        assert b"Profile updated successfully" in resp.data

        profile = Profile.query.filter_by(user_id=user_a.id).first()
        assert profile.first_name == "Alice"
        assert profile.last_name == "Wonderland"
        # strip_html removes the <script> *tags* (so it can never execute);
        # the inert text content remains and is auto-escaped on render.
        assert "<script>" not in profile.bio
        assert "This is my bio with" in profile.bio

    def test_user_cannot_edit_other_profile(self, client):
        """Negative/IDOR: user A editing user B's profile -> 403, no change."""
        user_a = create_user_with_profile("alice@test.com")
        user_b = create_user_with_profile("bob@test.com", first="Bob", last="Builder")
        login_as(client, user_a)

        resp = client.post(
            f"/profile/{user_b.id}/edit",
            data={
                "first_name": "Hacked",
                "last_name": "Account",
                "bio": "This should not work",
            },
            follow_redirects=False,
        )

        assert resp.status_code == 403

        profile_b = Profile.query.filter_by(user_id=user_b.id).first()
        assert profile_b.first_name == "Bob"
        assert profile_b.last_name == "Builder"

    def test_unauthenticated_user_cannot_edit_profile(self, client):
        """Negative: anonymous user cannot reach the edit route (401)."""
        user = create_user_with_profile("charlie@test.com")

        resp = client.get(f"/profile/{user.id}/edit")
        assert resp.status_code in (302, 401)

        resp = client.post(
            f"/profile/{user.id}/edit",
            data={"first_name": "Anonymous", "last_name": "Hacker"},
            follow_redirects=False,
        )
        assert resp.status_code in (302, 401)

    def test_edit_of_other_users_missing_profile_creates_nothing(self, client):
        """Regression: the edit route used to auto-create a Profile row for
        ANY user_id before checking ownership — an IDOR that let one user
        pollute another's account. Now: 403 and no row."""
        from werkzeug.security import generate_password_hash

        bare = User(
            email="bare@test.com",
            password_hash=generate_password_hash("testpass123"),
            role="buyer",
            status="active",
        )
        _db.session.add(bare)
        _db.session.commit()
        attacker = create_user_with_profile("polluter@test.com")
        login_as(client, attacker)

        resp = client.get(f"/profile/{bare.id}/edit")
        assert resp.status_code == 403
        assert Profile.query.filter_by(user_id=bare.id).count() == 0

    def test_own_missing_profile_returns_404(self, client):
        """Edge case: viewing one's OWN not-yet-created profile -> 404.
        (Another user's id would 403 before existence is ever checked.)"""
        from werkzeug.security import generate_password_hash

        user = User(
            email="noprofile@test.com",
            password_hash=generate_password_hash("testpass123"),
            role="buyer",
            status="active",
        )
        _db.session.add(user)
        _db.session.commit()
        login_as(client, user)

        resp = client.get(f"/profile/{user.id}")
        assert resp.status_code == 404


class TestProfileViewPrivacy:
    """SFR-03 / NFSR-01: profile pages are own-only (admins excepted) —
    they carry personal data (name, phone, address) and were previously
    world-readable."""

    def test_owner_can_view_own_profile(self, client):
        user = create_user_with_profile("owner@test.com", first="Olivia")
        login_as(client, user)

        resp = client.get(f"/profile/{user.id}")
        assert resp.status_code == 200
        assert b"Olivia" in resp.data

    def test_user_cannot_view_other_profile(self, client):
        target = create_user_with_profile("celeb@test.com", first="Famous")
        snooper = create_user_with_profile("snooper@test.com")
        login_as(client, snooper)

        resp = client.get(f"/profile/{target.id}")
        assert resp.status_code == 403
        assert b"Famous" not in resp.data

    def test_anonymous_cannot_view_profile(self, client):
        target = create_user_with_profile("hidden@test.com")

        resp = client.get(f"/profile/{target.id}")
        assert resp.status_code == 401

    def test_admin_can_view_any_profile(self, client):
        target = create_user_with_profile("watched@test.com", first="Watched")
        admin = create_user_with_profile("adminview@test.com")
        admin.role = "admin"
        _db.session.commit()
        login_as(client, admin)

        resp = client.get(f"/profile/{target.id}")
        assert resp.status_code == 200
        assert b"Watched" in resp.data
