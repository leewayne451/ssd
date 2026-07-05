import pytest

from app.models.product_listing import ProductListing
from app.models.enums import UserRole


def _login(client, user):
    with client.session_transaction() as sess:
        sess['user_id'] = user.id
        sess['role'] = user.role.value


def test_create_requires_login(client, db_session):
    resp = client.get('/seller/listings/create')
    assert resp.status_code == 401


def test_create_requires_seller(client, make_user):
    buyer = make_user('listing-buyer@test.local', role=UserRole.BUYER)
    _login(client, buyer)

    resp = client.get('/seller/listings/create')
    assert resp.status_code == 403


def test_create_listing_success(client, db_session, make_user):
    seller = make_user('listing-seller@test.local', role=UserRole.SELLER)
    _login(client, seller)

    data = {'title': 'Test Item', 'description': 'Nice', 'price': '12.50'}
    resp = client.post('/seller/listings/create', data=data, follow_redirects=False)
    # Should redirect to detail page
    assert resp.status_code == 302

    # Verify DB record exists
    item = db_session.query(ProductListing).filter_by(title='Test Item').one_or_none()
    assert item is not None
    assert item.seller_id == seller.id


def test_create_listing_with_image(client, db_session, make_user, tmp_path, app):
    seller = make_user('listing-img-seller@test.local', role=UserRole.SELLER)
    _login(client, seller)

    # Create a minimal PNG file
    png = b"\x89PNG\r\n\x1a\n" + b"data"
    data = {
        'title': 'Item With Image',
        'description': 'Has image',
        'price': '15.00'
    }

    from io import BytesIO
    img = (BytesIO(png), 'pic.png')

    resp = client.post('/seller/listings/create', data={**data, 'image': img}, content_type='multipart/form-data', follow_redirects=False)
    assert resp.status_code == 302

    # Verify uploaded_files record exists
    from app.models.uploaded_file import UploadedFile
    uf = db_session.query(UploadedFile).filter_by(original_filename='pic.png').one_or_none()
    assert uf is not None
    assert uf.listing_id is not None


def test_edit_requires_owner(client, db_session, make_user):
    # Create a listing owned by seller A
    from app.models.enums import ListingCondition

    seller_a = make_user('owner-a@test.local', role=UserRole.SELLER)
    seller_b = make_user('owner-b@test.local', role=UserRole.SELLER)

    listing = ProductListing(
        seller_id=seller_a.id,
        title='Own Me',
        description='x',
        price=1.0,
        category='misc',
        brand='b',
        condition=ListingCondition.PRE_OWNED,
    )
    db_session.add(listing)
    db_session.commit()

    # Sign in as a different seller
    _login(client, seller_b)

    resp = client.get(f'/seller/listings/{listing.id}/edit')
    assert resp.status_code == 403


def test_edit_owner_success(client, db_session, make_user):
    from app.models.enums import ListingCondition

    seller = make_user('owner-c@test.local', role=UserRole.SELLER)

    listing = ProductListing(
        seller_id=seller.id,
        title='Mine',
        description='old',
        price=5.0,
        category='misc',
        brand='b',
        condition=ListingCondition.PRE_OWNED,
    )
    db_session.add(listing)
    db_session.commit()

    _login(client, seller)

    data = {'title': 'Mine Updated', 'description': 'new', 'price': '6.00'}
    resp = client.post(f'/seller/listings/{listing.id}/edit', data=data, follow_redirects=False)
    assert resp.status_code == 302

    updated = db_session.get(ProductListing, listing.id)
    assert updated.title == 'Mine Updated'
