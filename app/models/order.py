from app.extensions import db
from app.models.enums import WorkflowStatus, PaymentStatus


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    listing_id = db.Column(db.Integer, db.ForeignKey("product_listings.id"), nullable=False)
    committed_price = db.Column(db.Numeric(10, 2), nullable=False)
    workflow_status = db.Column(db.Enum(WorkflowStatus), nullable=False, default=WorkflowStatus.COMMITTED)
    payment_status = db.Column(db.Enum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now(), onupdate=db.func.now())
