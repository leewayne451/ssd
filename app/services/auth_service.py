"""auth_service — registration, login/logout and request identity (FR-01/02).

Enforces the password policy at registration, one generic error for every
credential failure (no account enumeration), progressive lockout (FSR-05),
suspended-account denial (FR-13), session regeneration against fixation,
and audits every auth event (FSR-13). get_current_user() is the single
request-identity accessor, delegating to rbac's fail-closed loader.
"""

from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session, request

from app.models.user import User
from app.models.profile import Profile
from app.models.enums import AccountStatus
from app.extensions import db
from app.services.user_service import (
    get_user_by_email,
    get_user_by_id,
    create_user,
    update_last_login,
    record_failed_attempt,
    reset_failed_attempts,
    is_account_locked
)

from app.security.password_policy import validate_password
from app.security.rate_limit import get_lockout_duration, should_lock_account
from app.security.session_policy import regenerate_session, set_activity_timestamp
from app.services.audit_service import record

# One generic message for every credential failure — never reveal whether the
# email exists, the password was wrong, or the account is suspended.
_GENERIC_LOGIN_ERROR = "Invalid email or password."


def register_user(email: str, password: str, name: str = "", phone: str = "") -> tuple[User | None, str | None]:
    """Returns (user, error_message). Creates the User and their Profile (FR-01)."""
    # Check if email exists
    if get_user_by_email(email):
        return None, "Email already registered."

    # Validate password
    is_valid, error = validate_password(password)
    if not is_valid:
        return None, error

    # Hash password
    password_hash = generate_password_hash(password)

    # Create user
    user = create_user(email, password_hash)

    # FR-01: the account's Profile (name, phone) is created at registration so
    # a user never exists without one.
    parts = (name or "").strip().split(None, 1)
    profile = Profile(
        user_id=user.id,
        first_name=parts[0] if parts else "",
        last_name=parts[1] if len(parts) > 1 else "",
        phone_number=(phone or "").strip() or None,
    )
    db.session.add(profile)
    db.session.commit()

    record(user, "user_registered", "user", user.id)

    return user, None

def login_user(email: str, password: str) -> tuple[User | None, str | None]:
    """Returns (user, error_message)."""
    user = get_user_by_email(email)

    # User not found
    if not user:
        record(None, "login_failed", "user", None, {"reason": "user_not_found"})
        return None, _GENERIC_LOGIN_ERROR

    # Check if account is locked
    if is_account_locked(user):
        record(None, "login_failed", "user", user.id, {"reason": "account_locked"})
        return None, "Account is temporarily locked. Please try again later."

    # Verify password
    if not check_password_hash(user.password_hash, password):
        # Record failed attempt
        record_failed_attempt(user)
        record(None, "login_failed", "user", user.id, {"reason": "wrong_password"})

        # Apply lockout if needed
        if should_lock_account(user.failed_login_attempts):
            duration = get_lockout_duration(user.failed_login_attempts)
            if duration:
                user.locked_until = datetime.now(timezone.utc) + duration
                db.session.commit()
                record(None, "account_locked", "user", user.id,
                       {"attempts": user.failed_login_attempts})
            return None, "Too many failed attempts. Account temporarily locked."

        return None, _GENERIC_LOGIN_ERROR

    # FR-13 / CONFLICT-002: suspended accounts must not log in. Checked after
    # password verification, with the generic error, so account status is not
    # leaked to password-guessers.
    if user.status == AccountStatus.SUSPENDED:
        record(None, "login_failed", "user", user.id, {"reason": "suspended"})
        try:
            from app.services.security_event_service import record as record_event
            record_event(user, "suspended_login_denied", "login rejected: account suspended")
        except Exception:  # nosec B110 - logging must never break login
            pass
        return None, _GENERIC_LOGIN_ERROR

    # Success! Reset attempts, update last_login
    reset_failed_attempts(user)
    update_last_login(user)

    # Regenerate session (prevent fixation: a fresh session cookie is issued,
    # discarding any pre-login session content an attacker may have planted)
    regenerate_session()

    # Store user info in session
    session['user_id'] = user.id
    session['role'] = user.role
    set_activity_timestamp()

    record(user, "login_success", "user", user.id)

    return user, None

def change_password(user, current_password: str, new_password: str) -> tuple[bool, str | None]:
    """Rotate `user`'s password (FR-02). Returns (ok, error).

    Requires proof of the current password, enforces the full policy on the
    new one (FSR-02), rejects reuse, clears any forced-rotation flag (the
    bootstrap credential dies here) and audits the change.
    """
    if user is None:
        return False, "You must be logged in."

    if not check_password_hash(user.password_hash, current_password or ""):
        record(user, "password_change_failed", "user", user.id,
               {"reason": "wrong_current_password"})
        return False, "Current password is incorrect."

    is_valid, error = validate_password(new_password or "")
    if not is_valid:
        return False, error

    if check_password_hash(user.password_hash, new_password):
        return False, "The new password must be different from the current one."

    user.password_hash = generate_password_hash(new_password)
    user.must_change_password = False
    db.session.commit()

    record(user, "password_changed", "user", user.id)
    return True, None


def logout_user() -> None:
    """Log out the current user."""
    user_id = session.get('user_id')
    if user_id:
        user = get_user_by_id(user_id)
        if user:
            record(user, "logout", "user", user.id)

    session.clear()

def get_current_user():
    """
    Helper to get the current user for this request.

    Delegates to rbac.load_current_user so the whole request shares one
    DB lookup (cached on the request) and one fail-closed policy: stale or
    suspended sessions are cleared and treated as anonymous.
    """
    from app.security.rbac import load_current_user
    return load_current_user()
