"""Order entity — a buyer's purchase commitment (FR-09)."""

from app.extensions import db
from app.models.enums import WorkflowStatus, PaymentStatus


class Order(db.Model):
    """A buyer's purchase commitment (FR-09).

    committed_price is captured server-side from the listing at commit time
    (D1 9.3.1: client prices are never trusted). workflow_status moves only
    through workflow_service's audited H-3 state machine; payment_status
    only through checkout_service (9.3.4 simulated payment).
    """
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    listing_id = db.Column(db.Integer, db.ForeignKey("product_listings.id"), nullable=False)
    committed_price = db.Column(db.Numeric(10, 2), nullable=False)
    workflow_status = db.Column(db.Enum(WorkflowStatus), nullable=False, default=WorkflowStatus.COMMITTED)
    payment_status = db.Column(db.Enum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now(), onupdate=db.func.now())
