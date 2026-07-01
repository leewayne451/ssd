"""
Château Collective — Ownership / IDOR enforcement (M2)

Owner-scoped resources (a user's profile, cart, orders, a seller's listings)
must only be reachable by the user who owns them. The primary helper is
``assert_owner`` which routes call inline once they have loaded a resource:

    from app.security.ownership import assert_owner

    listing = get_listing_by_id(listing_id)
    if not listing:
        abort(404)
    assert_owner(listing, current_user, owner_attr="seller_id")

A convenience decorator ``ownership_required`` is also provided for the common
"load by URL id, then check owner" pattern:

    @bp.route("/orders/<int:order_id>")
    @ownership_required(get_order_by_id, id_param="order_id", owner_attr="buyer_id")
    def view_order(order_id):
        ...

Both fail closed: a missing/None owner id, or a mismatch, yields 403 (and the
attempt is recorded as a security event). A missing resource yields 404.
"""

import logging
from functools import wraps

from flask import abort

logger = logging.getLogger(__name__)

# Attributes inspected, in order, when no explicit ``owner_attr`` is given.
_OWNER_ATTRS = ("user_id", "owner_id", "seller_id", "buyer_id", "actor_user_id")


def _get_attr(resource, attr):
    """Read ``attr`` from a model object or a plain dict."""
    if isinstance(resource, dict):
        return resource.get(attr)
    return getattr(resource, attr, None)


def _infer_owner_id(resource):
    """Best-effort owner id when the caller did not name the owner attribute."""
    for attr in _OWNER_ATTRS:
        value = _get_attr(resource, attr)
        if value is not None:
            return value
    return None


def _current_user_id(current_user):
    """Accept a User object, a bare id, or None."""
    if current_user is None:
        return None
    return getattr(current_user, "id", current_user)


def _log_idor_attempt(resource, owner_attr):
    """Record an IDOR/ownership-violation security event. Never raises."""
    try:
        from app.services.security_event_service import record as record_event
        from app.services.auth_service import get_current_user

        target = type(resource).__name__ if not isinstance(resource, dict) else "dict"
        record_event(
            get_current_user(),
            "ownership_denied",
            f"attempted access to {target} not owned by current user (owner_attr={owner_attr})",
        )
    except Exception:
        # Logging must never break the request it is protecting.
        logger.debug("failed to record ownership_denied security event", exc_info=True)


def assert_owner(resource, current_user, owner_attr=None):
    """
    Abort the request unless ``current_user`` owns ``resource``.

    Args:
        resource:     the loaded resource (model object or dict). None -> 404.
        current_user: a User object, a user id, or None. None -> 401.
        owner_attr:   name of the attribute/key holding the owner's user id.
                      When omitted, a small set of common names is tried.

    Returns:
        True when ownership holds (so callers may use it in a boolean context).
    """
    if resource is None:
        abort(404)

    user_id = _current_user_id(current_user)
    if user_id is None:
        abort(401)

    if owner_attr is not None:
        owner_id = _get_attr(resource, owner_attr)
    else:
        owner_id = _infer_owner_id(resource)

    # Fail closed: unknown owner is treated as "not yours".
    if owner_id is None or owner_id != user_id:
        _log_idor_attempt(resource, owner_attr)
        abort(403)

    return True


def ownership_required(loader, id_param="id", owner_attr=None):
    """
    Decorator: load a resource by its URL id then enforce ownership.

    Args:
        loader:     callable(resource_id) -> resource (or None).
        id_param:   name of the view kwarg carrying the resource id.
        owner_attr: forwarded to ``assert_owner``.
    """

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            from app.services.auth_service import get_current_user

            user = get_current_user()
            if user is None:
                abort(401)

            resource = loader(kwargs.get(id_param))
            assert_owner(resource, user, owner_attr=owner_attr)
            return fn(*args, **kwargs)

        return wrapper

    return decorator
