from app.extensions import db
from app.models.enums import UserRole, AccountStatus
from datetime import datetime


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.BUYER)
    status = db.Column(db.Enum(AccountStatus), nullable=False, default=AccountStatus.ACTIVE)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now(), onupdate=db.func.now())
    
    # Track last successful login
    last_login = db.Column(db.DateTime(timezone=True), nullable=True)
    
    # Rate limiting / lockout fields
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime(timezone=True), nullable=True)
    
    # Email confirmation
    email_confirmed = db.Column(db.Boolean, default=False)
    email_confirmed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    profile = db.relationship("Profile", back_populates="user", uselist=False)