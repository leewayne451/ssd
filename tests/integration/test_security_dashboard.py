"""Admin dashboard counters (FR-12) + security dashboard (NFSR-20).

UI-audit items 7+10: the admin landing page now carries live queue counters,
and /admin/security aggregates the app-level SecurityEvent signals (lockouts,
access denials, rejected sessions…) as the D1 §9.3.6 alert surface. Both stay
behind the standard role+2FA gate.
"""

import time

from app.extensions import db
from app.models.enums import ApprovalStatus, ListingCondition, UserRole
from app.models.product_listing import ProductListing
from app.models.user import User
from app.security import admin_2fa
from app.services.security_event_service import record as record_event


def _make_admin_verified(client):
    secret = admin_2fa.generate_secret()
    admin = User(
        email=f"admin{time.time_ns()}@example.com", password_hash="x",
        role=UserRole.ADMIN, status="active",
        totp_secret=secret, totp_enabled=True,
    )
    db.session.add(admin)
    db.session.commit()
    with client.session_transaction() as sess:
        sess["user_id"] = admin.id
        sess["role"] = "admin"
        sess[admin_2fa.SESSION_2FA_FLAG] = True
    return admin


def test_admin_index_shows_live_queue_counters(client, db_session):
    _make_admin_verified(client)
    seller = User(email="counterseller@example.com", password_hash="x",
                  role=UserRole.SELLER, status="active")
    db.session.add(seller)
    db.session.commit()
    for i in range(3):
        db.session.add(ProductListing(
            seller_id=seller.id, title=f"Pending {i}", description="d",
            category="bags", brand="B", price=10.0,
            condition=ListingCondition.PRE_OWNED,
            approval_status=ApprovalStatus.PENDING,
        ))
    db.session.commit()

    resp = client.get("/admin/")
    assert resp.status_code == 200
    assert b"listings pending approval" in resp.data
    assert b'<div class="fs-3 fw-bold">3</div>' in resp.data
    assert b"security events, last 24" in resp.data


def test_security_dashboard_aggregates_events(client, db_session):
    _make_admin_verified(client)
    for _ in range(4):
        record_event(None, "access_denied", "role required")
    record_event(None, "listing_reported", "listing 1 reported")

    resp = client.get("/admin/security")
    assert resp.status_code == 200
    assert b"access_denied" in resp.data
    assert b"listing_reported" in resp.data
    # The dominant type gets the full-width meter class.
    assert b"meter-fill p100" in resp.data
    # Edge-layer framing: nginx blocks are evidence, not DB rows.
    assert b"rate-limiting" in resp.data


def test_security_dashboard_gated(client, db_session, login_as):
    assert client.get("/admin/security").status_code == 401
    login_as("plainviewer@example.com")
    assert client.get("/admin/security").status_code == 403
