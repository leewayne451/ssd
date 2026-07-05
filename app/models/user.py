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

    # Admin two-factor authentication (TOTP) — see app/security/admin_2fa.py.
    # Secret is the base32 seed shared with the authenticator app; should be
    # encrypted at rest in production. totp_enabled flips on once enrolment is
    # confirmed with a valid code.
    totp_secret = db.Column(db.String(64), nullable=True)
    totp_enabled = db.Column(db.Boolean, nullable=False, default=False)

    # Relationships
    profile = db.relationship("Profile", back_populates="user", uselist=False)