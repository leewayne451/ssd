from app.extensions import db


class Shipment(db.Model):
    __tablename__ = "shipments"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), unique=True, nullable=False)
    tracking_number = db.Column(db.String(100))
    shipped_at = db.Column(db.DateTime)
    received_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now(), onupdate=db.func.now())
