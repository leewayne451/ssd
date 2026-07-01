# Session policy — secure cookie flags, inactivity timeout, session regeneration.
from flask import session, request, current_app
from datetime import datetime, timezone, timedelta

def regenerate_session() -> None:
    """Regenerate session ID to prevent session fixation."""
    session.clear()

def set_activity_timestamp() -> None:
    """Store the last activity timestamp in session."""
    session['last_activity'] = datetime.now(timezone.utc).isoformat()

def check_inactivity_timeout() -> bool:
    """
    Check if the session has timed out due to inactivity.
    Returns True if session is still valid.
    """
    if 'last_activity' not in session:
        return True
    
    last_activity = datetime.fromisoformat(session['last_activity'])
    aware_last_activity = last_activity.replace(tzinfo=timezone.utc)
    
    timeout_minutes = current_app.config.get('SESSION_TIMEOUT_MINUTES', 30)
    if datetime.now(timezone.utc) - aware_last_activity > timedelta(minutes=timeout_minutes):
        session.clear()
        return False
    return True

def apply_cookie_flags(app):
    """Apply secure cookie flags in production."""
    # These are already in config.py, but ensure they're set
    app.config.setdefault('SESSION_COOKIE_HTTPONLY', True)
    app.config.setdefault('SESSION_COOKIE_SAMESITE', 'Lax')
    # Secure is set per environment (False in dev, True in prod)