"""Moderation reasons end-to-end (FR-14 / SFR-14 — UI-audit items 8+9).

Buyers can now say WHY a listing is suspicious, admins see that reason in
the moderation queue, and the admin rejection form finally carries the
reason field the route/audit always supported. Reasons stay internal:
they never render on public or seller pages.
"""

import time

from app.extensions import db
from app.models.audit_log import AuditLog
from app.models.enums import ApprovalStatus, ListingCondition, UserRole
from app.models.product_listing import ProductListing
from app.models.user import User
from app.security import admin_2fa


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


def _listing(approval=ApprovalStatus.APPROVED, title="Reportable bag"):
    seller = User(email=f"s{time.time_ns()}@example.com", password_hash="x",
                  role=UserRole.SELLER, status="active")
    db.session.add(seller)
    db.session.commit()
    listing = ProductListing(
        seller_id=seller.id, title=title, description="d",
        category="bags", brand="B", price=10.0,
        condition=ListingCondition.PRE_OWNED, approval_status=approval,
    )
    db.session.add(listing)
    db.session.commit()
    return listing


def test_report_reason_flows_from_buyer_to_admin_queue(client, db_session, login_as):
    listing = _listing()
    login_as("concerned@example.com")

    resp = client.post(
        f"/listings/{listing.id}/report",
        data={"reason": "SUSPICIOUS-serial-number-looks-fake"},
        follow_redirects=True,
    )
    assert resp.status_code == 200

    db.session.refresh(listing)
    assert listing.reported is True
    assert listing.report_reason == "SUSPICIOUS-serial-number-looks-fake"

    _make_admin_verified(client)
    page = client.get("/admin/listings")
    assert page.status_code == 200
    assert b"SUSPICIOUS-serial-number-looks-fake" in page.data


def test_report_reason_never_shown_publicly(client, db_session, login_as):
    listing = _listing()
    login_as("reporter2@example.com")
    client.post(f"/listings/{listing.id}/report",
                data={"reason": "INTERNAL-REPORT-REASON"}, follow_redirects=True)

    public = client.get(f"/listings/{listing.id}")
    assert public.status_code == 200
    assert b"INTERNAL-REPORT-REASON" not in public.data


def test_reject_form_reason_reaches_audit_log(client, db_session):
    _make_admin_verified(client)
    listing = _listing(approval=ApprovalStatus.PENDING, title="Reject me")

    resp = client.post(
        f"/admin/listings/{listing.id}/reject",
        data={"reason": "counterfeit stitching pattern"},
    )
    assert resp.status_code == 302

    db.session.refresh(listing)
    assert listing.approval_status == ApprovalStatus.REJECTED

    row = AuditLog.query.filter_by(
        action_type="listing_rejected", target_id=listing.id
    ).first()
    assert row is not None
    assert "counterfeit stitching pattern" in (row.details or "")
