from io import BytesIO
from app.security.file_validation import validate_upload


def make_file(filename: str, content: bytes):
    f = BytesIO(content)
    f.filename = filename
    return f


def test_validate_png_passes():
    # PNG header
    data = b"\x89PNG\r\n\x1a\n" + b"rest"
    f = make_file("image.png", data)
    errs = validate_upload(f)
    assert errs == []


def test_validate_extension_mismatch():
    # PNG content but .jpg extension
    data = b"\x89PNG\r\n\x1a\n" + b"rest"
    f = make_file("image.jpg", data)
    errs = validate_upload(f)
    assert any("does not match" in e for e in errs)


def test_validate_oversize():
    data = b"\x89PNG\r\n\x1a\n" + b"x" * (5 * 1024 * 1024 + 1)
    f = make_file("image.png", data)
    errs = validate_upload(f)
    assert any("exceeds the 5 MB" in e for e in errs)
