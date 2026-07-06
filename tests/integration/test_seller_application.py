"""M10 — seller application lifecycle (FR-04 / SFR-04, D1 UC-02).

A buyer applies to become a seller; an admin (role + 2FA gated) approves or
rejects. Approval promotes the account to the seller role server-side, and
every review decision writes an AuditLog row (FSR-11/12). Application details
stay visible only to the applicant and administrators (SFR-04).
"""

import time

from app.extensions import db
from app.models.audit_log import AuditLog
from app.models.enums import ApprovalStatus, UserRole
from app.models.seller_application import SellerApplication
from app.models.user import User
from app.security import admin_2fa
from app.services import seller_service


def _make_admin_verified(client):
    """Create an enrolled admin and mark this client's session 2FA-verified."""
    secret = admin_2fa.generate_secret()
    admin = User(
        email=f"admin{time.time_ns()}@example.com",
        password_hash="x",
        role=UserRole.ADMIN,
        status="active",
        totp_secret=secret,
        totp_enabled=True,
    )
    db.session.add(admin)
    db.session.commit()
    with client.session_transaction() as sess:
        sess["user_id"] = admin.id
        sess["role"] = "admin"
        sess[admin_2fa.SESSION_2FA_FLAG] = True
    return admin


# ------------------- applying (FR-04) ---------------------------------------

def test_buyer_can_apply_and_application_is_pending(client, login_as):
    buyer = login_as("applicant@example.com")

    resp = client.post(
        "/seller/apply",
        data={"reason": "I deal in vintage watches."},
        follow_redirects=True,
    )
    assert resp.status_code == 200

    application = SellerApplication.query.filter_by(user_id=buyer.id).one()
    assert application.status == ApprovalStatus.PENDING

    row = AuditLog.query.filter_by(
        action_type="seller_application_submitted", target_id=application.id
    ).first()
    assert row is not None and row.actor_user_id == buyer.id


def test_anonymous_cannot_reach_apply(client, db_session):
    assert client.get("/seller/apply").status_code == 401
    assert client.post("/seller/apply", data={"reason": "x"}).status_code == 401


def test_seller_cannot_apply_again(client, login_as):
    seller = login_as("alreadyseller@example.com", role=UserRole.SELLER)

    client.post("/seller/apply", data={"reason": "more"}, follow_redirects=True)
    assert SellerApplication.query.filter_by(user_id=seller.id).count() == 0


def test_duplicate_pending_application_blocked(client, login_as):
    buyer = login_as("eager@example.com")

    client.post("/seller/apply", data={"reason": "first"}, follow_redirects=True)
    client.post("/seller/apply", data={"reason": "second"}, follow_redirects=True)

    assert SellerApplication.query.filter_by(user_id=buyer.id).count() == 1


def test_empty_reason_rejected(client, login_as):
    buyer = login_as("terse@example.com")

    client.post("/seller/apply", data={"reason": "   "}, follow_redirects=True)
    assert SellerApplication.query.filter_by(user_id=buyer.id).count() == 0


# ------------------- admin review (SFR-04 / FSR-10) -------------------------

def test_admin_approve_promotes_applicant_and_audits(client, db_session):
    applicant = User(email="hopeful@example.com", password_hash="x",
                     role=UserRole.BUYER, status="active")
    db.session.add(applicant)
    db.session.commit()
    application, err = seller_service.apply_to_become_seller(applicant, "please")
    assert err is None

    admin = _make_admin_verified(client)
    resp = client.post(f"/admin/seller-applications/{application.id}/approve")
    assert resp.status_code == 302

    db.session.refresh(applicant)
    db.session.refresh(application)
    assert applicant.role == UserRole.SELLER
    assert application.status == ApprovalStatus.APPROVED
    assert application.reviewed_by_admin_id == admin.id

    row = AuditLog.query.filter_by(
        action_type="seller_application_approved", target_id=application.id
    ).first()
    assert row is not None and row.actor_user_id == admin.id


def test_admin_reject_keeps_buyer_role_and_allows_reapply(client, db_session):
    applicant = User(email="rejected@example.com", password_hash="x",
                     role=UserRole.BUYER, status="active")
    db.session.add(applicant)
    db.session.commit()
    application, _ = seller_service.apply_to_become_seller(applicant, "please")

    _make_admin_verified(client)
    resp = client.post(f"/admin/seller-applications/{application.id}/reject")
    assert resp.status_code == 302

    db.session.refresh(applicant)
    db.session.refresh(application)
    assert applicant.role == UserRole.BUYER
    assert application.status == ApprovalStatus.REJECTED

    # A rejected applicant may try again (fresh row, old one preserved).
    second, err = seller_service.apply_to_become_seller(applicant, "second try")
    assert err is None and second.id != application.id


def test_non_admin_cannot_review_applications(client, login_as, db_session):
    applicant = User(email="target@example.com", password_hash="x",
                     role=UserRole.BUYER, status="active")
    db.session.add(applicant)
    db.session.commit()
    application, _ = seller_service.apply_to_become_seller(applicant, "please")

    login_as("nosyseller@example.com", role=UserRole.SELLER)
    assert client.get("/admin/seller-applications").status_code == 403
    assert client.post(
        f"/admin/seller-applications/{application.id}/approve"
    ).status_code == 403

    db.session.refresh(application)
    assert application.status == ApprovalStatus.PENDING


def test_already_reviewed_application_cannot_be_reapproved(client, db_session):
    applicant = User(email="double@example.com", password_hash="x",
                     role=UserRole.BUYER, status="active")
    db.session.add(applicant)
    db.session.commit()
    application, _ = seller_service.apply_to_become_seller(applicant, "please")

    admin = _make_admin_verified(client)
    seller_service.reject_application(admin, application.id)

    resp = client.post(
        f"/admin/seller-applications/{application.id}/approve",
        follow_redirects=True,
    )
    assert resp.status_code == 200  # redirected back with a flash error

    db.session.refresh(applicant)
    assert applicant.role == UserRole.BUYER  # rejection stands


# ------------------- confidentiality (SFR-04) -------------------------------

def test_applicant_sees_only_their_own_application(client, db_session, login_as):
    other = User(email="other@example.com", password_hash="x",
                 role=UserRole.BUYER, status="active")
    db.session.add(other)
    db.session.commit()
    seller_service.apply_to_become_seller(other, "SECRET-OTHER-REASON")

    login_as("me@example.com")
    resp = client.get("/seller/apply")
    assert resp.status_code == 200
    assert b"SECRET-OTHER-REASON" not in resp.data
