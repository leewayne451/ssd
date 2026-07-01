"""
Château Collective — Role-Based Access Control (M2)

Canonical home for the access-control decorators every protected route imports:

    from app.security.rbac import login_required, role_required

    @bp.route("/admin")
    @role_required("admin")
    def admin_home():
        ...

Behaviour (kept stable so existing route tests keep passing):
  * Unauthenticated request  -> 401
  * Authenticated, wrong role -> 403 (and a `security_event` is recorded)

Roles may be passed as plain strings ("seller") or `UserRole` members
(`UserRole.SELLER`); both are normalised to their string value before
comparison, and the value stored in the session is normalised the same way.
"""

import logging
from functools import wraps

from flask import session, abort

from app.models.enums import UserRole

logger = logging.getLogger(__name__)


def _role_value(role):
    """Normalise a role (UserRole member or str) to its plain string value."""
    if role is None:
        return None
    if isinstance(role, UserRole):
        return role.value
    # str-Enum members and bare strings both land here.
    value = getattr(role, "value", role)
    return str(value)


def current_user_role():
    """Return the current request's role as a plain string, or None."""
    return _role_value(session.get("role"))


def is_authenticated():
    """True if a user id is present in the session."""
    return bool(session.get("user_id"))


def _log_access_denied(required_roles):
    """Record an access-denied security event. Never raises."""
    try:
        from app.services.security_event_service import record as record_event
        from app.services.auth_service import get_current_user

        record_event(
            get_current_user(),
            "access_denied",
            f"role required: {sorted(required_roles)}; had: {current_user_role()}",
        )
    except Exception:  # nosec B110 - security-event logging must never break the request
        # Logging must never break the request it is protecting.
        logger.debug("failed to record access_denied security event", exc_info=True)


def login_required(fn):
    """Restrict a view to authenticated users. Returns 401 when anonymous."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not is_authenticated():
            abort(401)
        return fn(*args, **kwargs)

    return wrapper


def role_required(*roles):
    """
    Restrict a view to users holding one of ``roles``.

    Anonymous -> 401; authenticated-but-wrong-role -> 403 (logged).
    """
    allowed = {_role_value(r) for r in roles}

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not is_authenticated():
                abort(401)
            if current_user_role() not in allowed:
                _log_access_denied(allowed)
                abort(403)
            return fn(*args, **kwargs)

        return wrapper

    return decorator
