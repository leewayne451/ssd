# Rate limiting — to be implemented with Flask-Limiter or custom middleware.
from datetime import datetime, timedelta

def get_lockout_duration(attempts: int) -> timedelta | None:
    """
    Returns the lockout duration based on number of failed attempts.
    Returns None if no lockout should be applied.
    """
    if attempts >= 10:
        return timedelta(minutes=60)   # 1 hour
    elif attempts >= 5:
        return timedelta(minutes=15)   # 15 minutes
    elif attempts >= 3:
        return timedelta(minutes=5)    # 5 minutes
    return None

def should_lock_account(attempts: int) -> bool:
    """Returns True if the account should be locked."""
    return attempts >= 3