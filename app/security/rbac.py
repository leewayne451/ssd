"""
Château Collective — Role-Based Access Control (M2)

Canonical home for the access-control decorators every protected route imports:

    from app.security.rbac import login_required, role_required

    @bp.route("/admin")
    @role_required("admin")
    def admin_home():
        ...

Behaviour:
  * Unauthenticated request        -> 401
  * Stale session (user deleted)   -> session cleared, 401 (never a 500)
  * Suspended account              -> session cleared, 401 (and a
    `security_event` is recorded) — suspension takes effect on the very
    next request, not the next login (FR-13 / CONFLICT-002)
  * Authenticated, wrong role      -> 403 (and a `security_event` is recorded)

Authorisation is decided against the **database** user (`user.role`,
`user.status`) resolved once per request and cached on ``flask.g`` — never
against values stored client-side in the session, which go stale the moment
an admin changes a role or suspends an account.

Roles may be passed as plain strings ("seller") or `UserRole` members
(`UserRole.SELLER`); both are normalised to their string value before
comparison.
"""

import logging
from functools import wraps

from flask import session, abort, request, has_request_context

from app.models.enums import UserRole, AccountStatus

logger = logging.getLogger(__name__)

# Cached on the *request* object, not flask.g: an app context can outlive many
# requests (long-lived contexts, test harnesses), and a cross-request cache
# would hand one user's identity to the next request.
_CACHE_ATTR = "_chateau_current_user"
_MISSING = object()


def _role_value(role):
    """Normalise a role (UserRole member or str) to its plain string value."""
    if role is None:
        return None
    if isinstance(role, UserRole):
        return role.value
    # str-Enum members and bare strings both land here.
    value = getattr(role, "value", role)
    return str(value)


def _record_security_event(actor, event_type, detail):
    """Record a security event. Never raises."""
    try:
        from app.services.security_event_service import record as record_event

        record_event(actor, event_type, detail)
    except Exception:  # nosec B110 - security logging must never break the request
        logger.debug("failed to record %s security event", event_type, exc_info=True)


def load_current_user():
    """
    Resolve the authenticated user for this request from the database.

    Returns the ``User`` row, or ``None`` when the request is anonymous.
    Resolved once per request and cached on the request object so decorators,
    views and the template context processor share a single query.

    Fails closed on the two poisoned-session cases:
      * ``user_id`` no longer matches a row (deleted account) — the session
        is cleared and the request is treated as anonymous instead of letting
        a view crash on ``current_user.id``.
      * the account is suspended — the session is cleared, a security event
        is recorded, and the request is treated as anonymous.
    """
    if not has_request_context():
        return None

    cached = getattr(request, _CACHE_ATTR, _MISSING)
    if cached is not _MISSING:
        return cached

    user_id = session.get("user_id")
    if not user_id:
        return None

    from app.services.user_service import get_user_by_id

    user = get_user_by_id(user_id)
    if user is None:
        # Stale session for a deleted account: fail closed as anonymous.
        _record_security_event(
            None, "stale_session_rejected", f"session referenced missing user id {user_id}"
        )
        session.clear()
        return None

    if user.status == AccountStatus.SUSPENDED:
        _record_security_event(
            user, "suspended_session_rejected", "request denied: account suspended"
        )
        session.clear()
        return None

    setattr(request, _CACHE_ATTR, user)
    return user


def current_user_role():
    """Return the current request's role as a plain string, or None."""
    user = load_current_user()
    if user is None:
        return None
    return _role_value(user.role)


def is_authenticated():
    """True if the session resolves to a live, non-suspended user."""
    return load_current_user() is not None


def _log_access_denied(required_roles):
    """Record an access-denied security event. Never raises."""
    _record_security_event(
        load_current_user(),
        "access_denied",
        f"role required: {sorted(required_roles)}; had: {current_user_role()}",
    )


def login_required(fn):
    """Restrict a view to authenticated users. Returns 401 when anonymous."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        if load_current_user() is None:
            abort(401)
        return fn(*args, **kwargs)

    return wrapper


def role_required(*roles):
    """
    Restrict a view to users holding one of ``roles`` **in the database**.

    Anonymous/stale/suspended -> 401; authenticated-but-wrong-role -> 403
    (logged). A role change made by an admin takes effect on the user's next
    request — no re-login required.
    """
    allowed = {_role_value(r) for r in roles}

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = load_current_user()
            if user is None:
                abort(401)
            if _role_value(user.role) not in allowed:
                _log_access_denied(allowed)
                abort(403)
            return fn(*args, **kwargs)

        return wrapper

    return decorator
