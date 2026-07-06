"""In-house authentication verdict entity (D1 §9.3.5)."""

from app.extensions import db
from app.models.enums import AuthenticationResult


class AuthenticationReview(db.Model):
    """An admin's in-house authentication verdict for an order (D1 §9.3.5).
    Notes are internal — routes expose them to admins only (SFR-14).
    """
    __tablename__ = "authentication_reviews"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    reviewed_by_admin_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    result = db.Column(db.Enum(AuthenticationResult), nullable=False)
    notes = db.Column(db.Text)
    reviewed_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
