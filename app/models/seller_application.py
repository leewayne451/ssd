from app.extensions import db
from app.models.enums import ApprovalStatus


class SellerApplication(db.Model):
    __tablename__ = "seller_applications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.Enum(ApprovalStatus), nullable=False, default=ApprovalStatus.PENDING)
    reviewed_by_admin_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    reviewed_at = db.Column(db.DateTime)
