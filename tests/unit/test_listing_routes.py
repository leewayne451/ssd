import pytest

from app.models.product_listing import ProductListing


def test_create_requires_login(client):
    resp = client.get('/seller/listings/create')
    assert resp.status_code == 401


def test_create_requires_seller(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 2
        sess['role'] = 'buyer'

    resp = client.get('/seller/listings/create')
    assert resp.status_code == 403


def test_create_listing_success(client, db_session):
    # Sign in as seller
    with client.session_transaction() as sess:
        sess['user_id'] = 10
        sess['role'] = 'seller'

    data = {'title': 'Test Item', 'description': 'Nice', 'price': '12.50'}
    resp = client.post('/seller/listings/create', data=data, follow_redirects=False)
    # Should redirect to detail page
    assert resp.status_code == 302

    # Verify DB record exists
    item = db_session.query(ProductListing).filter_by(title='Test Item').one_or_none()
    assert item is not None
    assert item.seller_id == 10


def test_create_listing_with_image(client, db_session, tmp_path, app):
    # Sign in as seller
    with client.session_transaction() as sess:
        sess['user_id'] = 11
        sess['role'] = 'seller'

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


def test_edit_requires_owner(client, db_session):
    # Create a listing owned by user 20
    from app.models.enums import ListingCondition

    listing = ProductListing(
        seller_id=20,
        title='Own Me',
        description='x',
        price=1.0,
        category='misc',
        brand='b',
        condition=ListingCondition.PRE_OWNED,
    )
    db_session.add(listing)
    db_session.commit()

    # Sign in as different seller
    with client.session_transaction() as sess:
        sess['user_id'] = 21
        sess['role'] = 'seller'

    resp = client.get(f'/seller/listings/{listing.id}/edit')
    assert resp.status_code == 403


def test_edit_owner_success(client, db_session):
    # Create a listing owned by user 30
    from app.models.enums import ListingCondition

    listing = ProductListing(
        seller_id=30,
        title='Mine',
        description='old',
        price=5.0,
        category='misc',
        brand='b',
        condition=ListingCondition.PRE_OWNED,
    )
    db_session.add(listing)
    db_session.commit()

    with client.session_transaction() as sess:
        sess['user_id'] = 30
        sess['role'] = 'seller'

    data = {'title': 'Mine Updated', 'description': 'new', 'price': '6.00'}
    resp = client.post(f'/seller/listings/{listing.id}/edit', data=data, follow_redirects=False)
    assert resp.status_code == 302

    updated = db_session.query(ProductListing).get(listing.id)
    assert updated.title == 'Mine Updated'
