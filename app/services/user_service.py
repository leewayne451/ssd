from datetime import datetime, timezone
from app.extensions import db
from app.models.user import User
from app.models.enums import UserRole

def get_user_by_email(email: str) -> User | None:
    return User.query.filter_by(email=email).first()

def get_user_by_id(user_id: int) -> User | None:
    return User.query.get(user_id)

def create_user(email: str, password_hash: str, role: str = UserRole.BUYER) -> User:
    user = User(
        email=email,
        password_hash=password_hash,
        role=role,
        status='active'
    )
    db.session.add(user)
    db.session.commit()
    return user

def update_last_login(user: User) -> None:
    user.last_login = datetime.now(timezone.utc)
    db.session.commit()

def record_failed_attempt(user: User) -> None:
    user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
    db.session.commit()

def reset_failed_attempts(user: User) -> None:
    user.failed_login_attempts = 0
    user.locked_until = None
    db.session.commit()

def is_account_locked(user: User) -> bool:
    if user.locked_until:
        # Convert naive DB datetime to aware UTC before comparing
        aware_locked_until = user.locked_until.replace(tzinfo=timezone.utc)
        return aware_locked_until > datetime.now(timezone.utc)
    return False