"""M3 — public discovery, approval visibility, search, upload hardening (T-14..T-21).

Locks in D1's "second-hand items stay hidden until admin approval"
(SFR-05/TRACE-003), validated search (FR-06/SFR-06), and end-to-end
upload safety (SDR-04).
"""

import re
from io import BytesIO

import pytest

from app.extensions import db
from app.models.enums import ApprovalStatus, ListingCondition, UserRole
from app.models.product_listing import ProductListing
from app.models.uploaded_file import UploadedFile

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"fakepixels"


def _listing(seller, title, approval=ApprovalStatus.APPROVED, brand="Hermes",
             category="bags", condition=ListingCondition.PRE_OWNED, price=100.0,
             active=True):
    obj = ProductListing(
        seller_id=seller.id, title=title, description=f"{title} description",
        category=category, brand=brand, price=price, condition=condition,
        approval_status=approval, is_active=active,
    )
    db.session.add(obj)
    db.session.commit()
    return obj


def _login(client, user):
    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["role"] = user.role.value


# ------------------- approval visibility (T-14, T-15) -----------------------

def test_public_index_hides_pending_and_rejected(client, db_session, make_user):
    """T-14: only admin-approved listings reach public browsing."""
    seller = make_user("vis-seller@test.local", role=UserRole.SELLER)
    _listing(seller, "Approved Bag", ApprovalStatus.APPROVED)
    _listing(seller, "Pending Bag", ApprovalStatus.PENDING)
    _listing(seller, "Rejected Bag", ApprovalStatus.REJECTED)
    _listing(seller, "Inactive Bag", ApprovalStatus.APPROVED, active=False)

    page = client.get("/listings")
    assert page.status_code == 200
    assert b"Approved Bag" in page.data
    assert b"Pending Bag" not in page.data
    assert b"Rejected Bag" not in page.data
    assert b"Inactive Bag" not in page.data


def test_detail_hidden_for_unapproved_except_owner_and_admin(client, db_session, make_user):
    """T-15: unapproved detail pages 404 publicly, stay visible to owner/admin."""
    seller = make_user("det-seller@test.local", role=UserRole.SELLER)
    other = make_user("det-other@test.local", role=UserRole.BUYER)
    admin = make_user("det-admin@test.local", role=UserRole.ADMIN)
    pending = _listing(seller, "Unseen Bag", ApprovalStatus.PENDING)

    # anonymous and unrelated users see nothing
    assert client.get(f"/listings/{pending.id}").status_code == 404
    _login(client, other)
    assert client.get(f"/listings/{pending.id}").status_code == 404

    # the owner still sees their pending listing
    _login(client, seller)
    assert client.get(f"/listings/{pending.id}").status_code == 200

    # and so does an admin (moderation)
    _login(client, admin)
    assert client.get(f"/listings/{pending.id}").status_code == 200


# ------------------- search & filtering (T-16, T-17) ------------------------

def test_search_filters_by_category_brand_condition_price(client, db_session, make_user):
    """T-16: FR-06 filters, each narrowing results server-side."""
    seller = make_user("search-seller@test.local", role=UserRole.SELLER)
    _listing(seller, "Birkin 25", brand="Hermes", category="bags",
             condition=ListingCondition.PRE_OWNED, price=15000)
    _listing(seller, "Submariner", brand="Rolex", category="watches",
             condition=ListingCondition.NEW, price=12000)
    _listing(seller, "Speedy 30", brand="Louis Vuitton", category="bags",
             condition=ListingCondition.PRE_OWNED, price=900)

    page = client.get("/listings?brand=Rolex")
    assert b"Submariner" in page.data and b"Birkin 25" not in page.data

    page = client.get("/listings?category=bags")
    assert b"Birkin 25" in page.data and b"Speedy 30" in page.data and b"Submariner" not in page.data

    page = client.get("/listings?condition=new")
    assert b"Submariner" in page.data and b"Birkin 25" not in page.data

    page = client.get("/listings?min_price=10000&max_price=13000")
    assert b"Submariner" in page.data and b"Speedy 30" not in page.data and b"Birkin 25" not in page.data

    page = client.get("/listings?q=Speedy")
    assert b"Speedy 30" in page.data and b"Submariner" not in page.data


def test_search_hostile_input_treated_as_data(client, db_session, make_user):
    """T-17: injection payloads return an empty, healthy result page."""
    seller = make_user("inj-seller@test.local", role=UserRole.SELLER)
    _listing(seller, "Honest Bag")

    for payload in ["' OR 1=1--", "\"; DROP TABLE product_listings;--", "<script>alert(1)</script>"]:
        page = client.get("/listings", query_string={"q": payload})
        assert page.status_code == 200
        assert b"Honest Bag" not in page.data  # treated as literal text, matches nothing
        assert b"<script>alert(1)</script>" not in page.data  # reflected output is escaped

    # garbage price values are coerced/dropped, not executed or crashed on
    assert client.get("/listings?min_price=abc&max_price='--").status_code == 200


# ------------------- upload hardening (T-18..T-21) ---------------------------

def _post_listing_with_file(client, filename, content):
    return client.post(
        "/seller/listings/create",
        data={
            "title": "Upload Test",
            "description": "d",
            "price": "10.00",
            "image": (BytesIO(content), filename),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )


def test_spoofed_magic_bytes_rejected_via_route(client, db_session, make_user):
    """T-18: a PHP payload named .png dies on the magic-byte check end-to-end."""
    seller = make_user("spoof-seller@test.local", role=UserRole.SELLER)
    _login(client, seller)

    resp = _post_listing_with_file(client, "shell.png", b"<?php system($_GET['c']); ?>")
    assert resp.status_code == 200
    assert UploadedFile.query.count() == 0
    assert b"upload failed" in resp.data


def test_disallowed_extension_rejected_via_route(client, db_session, make_user):
    seller = make_user("ext-seller@test.local", role=UserRole.SELLER)
    _login(client, seller)

    resp = _post_listing_with_file(client, "run.php", PNG_BYTES)
    assert UploadedFile.query.count() == 0
    assert b"upload failed" in resp.data


def test_traversal_filename_neutralised_and_stored_name_randomised(client, db_session, make_user):
    """T-19 + T-20: traversal names are flattened; stored name is uuid.ext."""
    seller = make_user("trav-seller@test.local", role=UserRole.SELLER)
    _login(client, seller)

    resp = _post_listing_with_file(client, "..\\..\\evil.png", PNG_BYTES)
    assert resp.status_code == 200

    uf = UploadedFile.query.first()
    assert uf is not None
    assert ".." not in uf.stored_filename
    assert uf.stored_filename != uf.original_filename
    assert re.fullmatch(r"[0-9a-f]{32}\.png", uf.stored_filename)


def test_media_route_rejects_traversal_and_unknown_names(client, db_session):
    """T-21: only server-generated names resolve; traversal shapes 404."""
    assert client.get("/listings/media/../../etc/passwd").status_code == 404
    assert client.get("/listings/media/..%2f..%2fetc%2fpasswd").status_code == 404
    assert client.get("/listings/media/notauuid.png").status_code == 404
    assert client.get("/listings/media/" + "a" * 32 + ".exe").status_code == 404


def test_media_route_serves_valid_upload(client, db_session, make_user, app):
    seller = make_user("serve-seller@test.local", role=UserRole.SELLER)
    _login(client, seller)
    _post_listing_with_file(client, "real.png", PNG_BYTES)

    uf = UploadedFile.query.first()
    assert uf is not None
    resp = client.get(f"/listings/media/{uf.stored_filename}")
    assert resp.status_code == 200
    assert resp.data.startswith(b"\x89PNG")
