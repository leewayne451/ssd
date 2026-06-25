from app.extensions import db
from app.models.enums import DisputeStatus


class Dispute(db.Model):
    __tablename__ = "disputes"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.Enum(DisputeStatus), nullable=False, default=DisputeStatus.OPEN)
    resolved_by_admin_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    resolution_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    resolved_at = db.Column(db.DateTime)
