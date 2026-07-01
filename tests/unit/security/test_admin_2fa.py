"""M2 — unit tests for the TOTP primitives behind admin 2FA."""

import base64

from app.security import admin_2fa


# RFC 6238 reference seed (ASCII "12345678901234567890") and its base32 form.
_RFC_SEED = b"12345678901234567890"
_RFC_SECRET = base64.b32encode(_RFC_SEED).decode("ascii")


def test_totp_matches_rfc6238_vector():
    # RFC 6238 SHA1 test vector at T=59 is 94287082; truncated to 6 digits.
    assert admin_2fa.totp_at(_RFC_SECRET, 59) == "287082"


def test_verify_accepts_current_code():
    assert admin_2fa.verify(_RFC_SECRET, "287082", for_time=59) is True


def test_verify_tolerates_one_step_drift():
    prev = admin_2fa.totp_at(_RFC_SECRET, 59 - 30)
    nxt = admin_2fa.totp_at(_RFC_SECRET, 59 + 30)
    assert admin_2fa.verify(_RFC_SECRET, prev, for_time=59) is True
    assert admin_2fa.verify(_RFC_SECRET, nxt, for_time=59) is True


def test_verify_rejects_wrong_and_malformed_codes():
    assert admin_2fa.verify(_RFC_SECRET, "000000", for_time=59) is False
    assert admin_2fa.verify(_RFC_SECRET, "12345", for_time=59) is False   # too short
    assert admin_2fa.verify(_RFC_SECRET, "abcdef", for_time=59) is False  # non-digit
    assert admin_2fa.verify(_RFC_SECRET, "", for_time=59) is False
    assert admin_2fa.verify("", "287082", for_time=59) is False


def test_verify_ignores_whitespace_in_entered_code():
    assert admin_2fa.verify(_RFC_SECRET, " 287 082 ", for_time=59) is True


def test_generate_secret_is_valid_base32_160_bit():
    secret = admin_2fa.generate_secret()
    assert len(base64.b32decode(secret)) == 20
    # Two fresh secrets should differ.
    assert secret != admin_2fa.generate_secret()


def test_provisioning_uri_shape():
    uri = admin_2fa.provisioning_uri(_RFC_SECRET, account_name="admin@example.com")
    assert uri.startswith("otpauth://totp/")
    assert f"secret={_RFC_SECRET}" in uri
    assert "issuer=" in uri
