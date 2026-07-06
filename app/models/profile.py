"""User profile entity — personal data kept apart from credentials."""

from app.extensions import db


class Profile(db.Model):
    """Personal data (name, phone, address, bio) split from the User
    credential row (NFR-13/NFR-14). Created at registration; own-only
    view/edit is enforced in profile_routes (SFR-03).
    """
    __tablename__ = "profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20))
    address = db.Column(db.Text)
    bio = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    updated_at = db.Column(
        db.DateTime, nullable=False, server_default=db.func.now(), onupdate=db.func.now()
    )

    user = db.relationship("User", back_populates="profile")
