from app.extensions import db
from app.models.enums import ApprovalStatus, ListingCondition, WorkflowStatus


class ProductListing(db.Model):
    __tablename__ = "product_listings"

    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    brand = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    condition = db.Column(db.Enum(ListingCondition), nullable=False)
    approval_status = db.Column(db.Enum(ApprovalStatus), nullable=False, default=ApprovalStatus.PENDING)
    workflow_status = db.Column(db.Enum(WorkflowStatus), nullable=False, default=WorkflowStatus.AVAILABLE)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now(), onupdate=db.func.now())
