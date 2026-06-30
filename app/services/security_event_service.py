# security_event_service — business logic layer.
from flask import request
from app.extensions import db
from app.models.security_event import SecurityEvent


def record(user, event_type, details=None):
    """
    Writes one row to the security_events table.

    user        = the current user (a User object), or None if anonymous/unauthenticated
    event_type  = short string, e.g. "login_failed", "lockout", "access_denied", "admin_2fa_failed"
    details     = optional string with extra context — NEVER put passwords/tokens/session ids here

    Never raises on failure to log — a broken security-event call should not break
    the route that called it.
    """
    try:
        entry = SecurityEvent(
            user_id=user.id if user else None,
            event_type=event_type,
            details=details,
            source_ip=request.remote_addr if request else None,
            user_agent=request.headers.get("User-Agent") if request else None,
        )
        db.session.add(entry)
        db.session.commit()
    except Exception:
        db.session.rollback()