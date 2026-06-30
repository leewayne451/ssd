"""
Château Collective — Access-control decorator shims.

The Phase-0 ``NotImplementedError`` stubs have been retired. The real
implementations now live in the security package; this module re-exports them
so existing imports (``from app.utils.decorators import role_required``) keep
working, and continues to host the ``current_user`` template helpers wired into
the app factory.

Prefer importing directly from the canonical modules in new code:

    from app.security.rbac import login_required, role_required
    from app.security.ownership import assert_owner, ownership_required
"""

from app.security.rbac import login_required, role_required  # noqa: F401
from app.security.ownership import assert_owner, ownership_required  # noqa: F401
from app.services.auth_service import get_current_user  # noqa: F401


def inject_current_user():
    """Context processor: expose ``current_user`` to every template."""
    return {"current_user": get_current_user()}
