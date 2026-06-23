"""
Château Collective — Audit logging stub (Phase 0)

Establishes the log_action() signature so that Phase 1+ code can call it
immediately. The implementation is a no-op here; Phase 1 will replace it
with a real AuditLog model write (see FSR-11, FSR-12, NFR-16 in D1).

Intended usage (Phase 1+):

    from app.utils.audit import log_action

    log_action(
        actor=current_user,
        action_type="user.suspend",
        target=target_user,
    )
"""

from typing import Any


def log_action(actor: Any, action_type: str, target: Any = None) -> None:
    """
    Record a security-relevant or business-critical action.

    Phase 0 no-op — does nothing. Replace with a real AuditLog model
    write in Phase 1 once the database models and session context exist.

    Args:
        actor:       The user (or system process) performing the action.
                     In Phase 1+ this will typically be the current_user object.
        action_type: A dot-namespaced string identifying the action,
                     e.g. 'user.login', 'listing.create', 'order.workflow_update',
                     'admin.suspend_user', 'dispute.resolve'.
        target:      The object the action was performed on (optional).
                     In Phase 1+ this could be a User, Listing, Order, etc.
    """
    # TODO (Phase 1): Persist to AuditLog table.
    # Required fields per FSR-12 / NFR-16:
    #   - actor identity (user id, email, or 'system')
    #   - timestamp (UTC)
    #   - action_type
    #   - target type + id
    #   - source IP (from request context where available)
    pass
