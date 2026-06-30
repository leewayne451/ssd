"""
Château Collective — Access-control decorators (Phase 0 stubs)

These decorators establish the intended API signatures so that Phase 1 routes
can import and use them immediately. The real logic requires the User model and
session structure from Phase 1, so the bodies raise NotImplementedError for now.

Intended usage (Phase 1+):

    from app.utils.decorators import role_required, ownership_required

    @bp.route("/admin/users")
    @role_required("admin")
    def admin_users():
        ...

    @bp.route("/listings/<int:listing_id>/edit")
    @role_required("seller")
    @ownership_required("listing", id_param="listing_id")
    def edit_listing(listing_id):
        ...
"""

from functools import wraps
from typing import Callable
from flask import session
from app.services.user_service import get_user_by_id


def role_required(*roles: str) -> Callable:
    """
    Decorator factory that restricts a route to users holding one of the
    given roles (e.g. 'buyer', 'seller', 'admin').

    Phase 0 stub — raises NotImplementedError until the User model and
    session helpers are in place (Phase 1).

    Args:
        *roles: One or more role strings that are permitted to access the view.

    Returns:
        A decorator that wraps the view function.
    """

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            raise NotImplementedError(
                "role_required is not yet implemented. "
                "Implement in Phase 1 once User model and session helpers exist."
            )

        return wrapper

    return decorator


def ownership_required(resource_type: str, id_param: str = "id") -> Callable:
    """
    Decorator that verifies the currently authenticated user owns the
    requested resource before allowing the view to proceed.

    Phase 0 stub — raises NotImplementedError until the relevant models
    and session helpers are in place (Phase 1).

    Args:
        resource_type: The type of resource to check ownership for
                       (e.g. 'listing', 'order', 'dispute').
        id_param:      The URL parameter name that carries the resource ID.
                       Defaults to 'id'.

    Returns:
        A decorator that wraps the view function.
    """

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            raise NotImplementedError(
                "ownership_required is not yet implemented. "
                "Implement in Phase 1 once the relevant models and session helpers exist."
            )

        return wrapper

    return decorator


def get_current_user():
    user_id = session.get('user_id')
    if user_id:
        return get_user_by_id(user_id)
    return None

def inject_current_user():
    return {'current_user': get_current_user()}