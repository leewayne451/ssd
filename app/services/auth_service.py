from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session, request

from app.models.user import User
from app.extensions import db
from app.services.user_service import (
    get_user_by_email,
    get_user_by_id,
    create_user,
    update_last_login,
    record_failed_attempt,
    reset_failed_attempts,
    is_account_locked
)

from app.security.password_policy import validate_password
from app.security.rate_limit import get_lockout_duration, should_lock_account
from app.security.session_policy import regenerate_session, set_activity_timestamp
from app.services.audit_service import record

def register_user(email: str, password: str) -> tuple[User | None, str | None]:
    """Returns (user, error_message)."""
    # Check if email exists
    if get_user_by_email(email):
        return None, "Email already registered."
    
    # Validate password
    is_valid, error = validate_password(password)
    if not is_valid:
        return None, error
    
    # Hash password
    password_hash = generate_password_hash(password)
    
    # Create user
    user = create_user(email, password_hash)
    
    # Audit log (stub - M5 will provide)
    # record(user.id, 'user_registered', user.email, {'ip': request.remote_addr})
    
    return user, None

def login_user(email: str, password: str) -> tuple[User | None, str | None]:
    """Returns (user, error_message)."""
    user = get_user_by_email(email)
    
    # User not found
    if not user:
        # Log failure
        # record(None, 'user_login_failed', email, {'ip': request.remote_addr, 'reason': 'user_not_found'})
        return None, "Invalid email or password."
    
    # Check if account is locked
    if is_account_locked(user):
        return None, "Account is temporarily locked. Please try again later."
    
    # Verify password
    if not check_password_hash(user.password_hash, password):
        # Record failed attempt
        record_failed_attempt(user)
        
        # Log failure
        # record(None, 'user_login_failed', user.email, {'ip': request.remote_addr, 'reason': 'wrong_password'})
        
        # Apply lockout if needed
        if should_lock_account(user.failed_login_attempts):
            duration = get_lockout_duration(user.failed_login_attempts)
            if duration:
                user.locked_until = datetime.now(timezone.utc) + duration
                db.session.commit()
            return None, "Too many failed attempts. Account temporarily locked."
        
        return None, "Invalid email or password."
    
    # Success! Reset attempts, update last_login
    reset_failed_attempts(user)
    update_last_login(user)
    
    # Regenerate session ID (prevent fixation)
    regenerate_session()
    
    # Store user info in session
    session['user_id'] = user.id
    session['role'] = user.role
    set_activity_timestamp()
    
    # Audit log
    # record(user.id, 'user_login', user.email, {'ip': request.remote_addr})
    
    return user, None

def logout_user() -> None:
    """Log out the current user."""
    user_id = session.get('user_id')
    if user_id:
        user = get_user_by_id(user_id)
        if user:
            # record(user.id, 'user_logout', user.email, {})
            pass
    
    session.clear()

def get_current_user():
    """Helper to get the current user from session."""
    from app.services.user_service import get_user_by_id
    user_id = session.get('user_id')
    if user_id:
        return get_user_by_id(user_id)
    return None