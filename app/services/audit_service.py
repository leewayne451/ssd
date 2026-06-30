# audit_service — business logic layer.
from flask import request
from app.extensions import db
from app.models.audit_log import AuditLog


def record(actor, action, target=None, target_id=None, meta=None):
    """
    Writes one row to the audit log.

    actor        = the current user (a User object), or None if anonymous/unauthenticated
    action_type  = short string, e.g. "login_success", "login_failed", "admin_delete_user"
    target_type  = what kind of thing was affected, e.g. "user", "order", "listing" (optional)
    target_id    = the id of that thing, e.g. 42 (optional)
    details      = optional string with extra context — NEVER put passwords/tokens/session ids here

    Never raises on failure to log — a broken audit call should not break
    the route that called it.
    """
    try:
        entry = AuditLog(
            actor_user_id=actor.id if actor else None,
            action_type=action,
            target_type=target,
            target_id=target_id,
            details=str(meta) if meta else None,
            source_ip=request.remote_addr if request else None,
            user_agent=request.headers.get("User-Agent") if request else None,
        )
        db.session.add(entry)
        db.session.commit()
    except Exception:
        db.session.rollback()
        # swallow the error — logging should never take down the caller's route
        # consider adding real error logging here (e.g. app.logger.exception(...))