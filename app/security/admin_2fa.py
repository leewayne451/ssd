"""
Château Collective — Admin two-factor authentication (M2)

Adds a second factor in front of the /admin area using TOTP (RFC 6238), the
same scheme as Google Authenticator / Authy / 1Password. We implement the
algorithm against the Python standard library (hmac + base64) so the
project gains a real, testable 2FA control without adding a third-party
dependency.

Two pieces:

  * Crypto helpers — generate a per-admin secret, build the otpauth:// URI a
    phone app scans, and verify a 6-digit code (with a +/-1 step skew window).
  * ``admin_2fa_required`` — a decorator that, *after* a role check, forces an
    admin to (a) enrol a secret and (b) verify a code once per session before
    any admin view runs.

Storage note: the base32 secret is held in ``User.totp_secret``. For a
production system this column should be encrypted at rest; for the D2 slice it
is stored plainly and never written to logs or audit details.
"""

import base64
import hmac
import secrets
import struct
import time
from functools import wraps
from urllib.parse import quote

from flask import session, redirect, url_for, request, flash, abort

from app.models.enums import UserRole

# --- TOTP parameters (RFC 6238 defaults) ---------------------------------
_DIGITS = 6
_PERIOD = 30          # seconds per step
_ALGORITHM = "sha1"   # what authenticator apps assume by default
_SKEW_STEPS = 1       # accept the previous/next step to tolerate clock drift

# Session flag set once a code has been verified for the current session.
SESSION_2FA_FLAG = "admin_2fa_verified"


# --- crypto helpers -------------------------------------------------------

def generate_secret(length_bytes: int = 20) -> str:
    """Return a fresh random base32 secret (default 160 bits, RFC-recommended)."""
    raw = secrets.token_bytes(length_bytes)
    return base64.b32encode(raw).decode("ascii")


def _hotp(secret_b32: str, counter: int) -> str:
    """RFC 4226 HOTP for a given counter, returned as a zero-padded code."""
    # base32 secrets are uppercase and may need re-padding to a multiple of 8.
    key = base64.b32decode(_normalise_secret(secret_b32))
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, _ALGORITHM).digest()
    offset = digest[-1] & 0x0F
    binary = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(binary % (10 ** _DIGITS)).zfill(_DIGITS)


def _normalise_secret(secret_b32: str) -> bytes:
    """Upper-case and pad a base32 secret so b32decode accepts it."""
    s = secret_b32.strip().replace(" ", "").upper()
    padding = (-len(s)) % 8
    return (s + "=" * padding).encode("ascii")


def totp_at(secret_b32: str, for_time: float) -> str:
    """The TOTP code valid at ``for_time`` (unix seconds)."""
    counter = int(for_time // _PERIOD)
    return _hotp(secret_b32, counter)


def verify(secret_b32: str, code: str, for_time: float | None = None) -> bool:
    """
    True if ``code`` matches the secret within the skew window.

    Comparison is constant-time and tolerant of whitespace in the entered code.
    """
    if not secret_b32 or not code:
        return False
    code = code.strip().replace(" ", "")
    if not code.isdigit() or len(code) != _DIGITS:
        return False

    now = time.time() if for_time is None else for_time
    counter = int(now // _PERIOD)
    for step in range(-_SKEW_STEPS, _SKEW_STEPS + 1):
        candidate = _hotp(secret_b32, counter + step)
        if hmac.compare_digest(candidate, code):
            return True
    return False


def provisioning_uri(secret_b32: str, account_name: str, issuer: str = "Chateau Collective") -> str:
    """
    Build the otpauth:// URI an authenticator app scans to enrol the secret.
    """
    label = quote(f"{issuer}:{account_name}")
    params = (
        f"secret={secret_b32}"
        f"&issuer={quote(issuer)}"
        f"&algorithm={_ALGORITHM.upper()}"
        f"&digits={_DIGITS}"
        f"&period={_PERIOD}"
    )
    return f"otpauth://totp/{label}?{params}"


# --- session / decorator --------------------------------------------------

def mark_verified():
    """Record that the current session has cleared the 2FA challenge."""
    session[SESSION_2FA_FLAG] = True


def is_verified() -> bool:
    return bool(session.get(SESSION_2FA_FLAG))


def clear_verified():
    session.pop(SESSION_2FA_FLAG, None)


def admin_2fa_required(fn):
    """
    Gate an admin view behind a verified second factor.

    Place *below* ``role_required("admin")`` so the role is checked first:

        @admin_bp.route("/")
        @role_required("admin")
        @admin_2fa_required
        def index():
            ...

    Behaviour for an authenticated admin:
      * no secret enrolled  -> redirect to the 2FA setup page
      * enrolled, unverified -> redirect to the 2FA verify page
      * enrolled and verified this session -> proceed
    """

    @wraps(fn)
    def wrapper(*args, **kwargs):
        from app.services.auth_service import get_current_user

        user = get_current_user()
        if user is None:
            abort(401)

        role = getattr(user.role, "value", user.role)
        if role != UserRole.ADMIN.value:
            abort(403)

        if not getattr(user, "totp_enabled", False) or not getattr(user, "totp_secret", None):
            flash("Two-factor authentication must be set up before accessing the admin area.", "warning")
            return redirect(url_for("admin_2fa.setup", next=request.path))

        if not is_verified():
            return redirect(url_for("admin_2fa.verify", next=request.path))

        return fn(*args, **kwargs)

    return wrapper
