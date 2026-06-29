from app.extensions import db


class OrderStatusHistory(db.Model):
    __tablename__ = "order_status_history"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    actor_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    old_status = db.Column(db.String(50), nullable=False)
    new_status = db.Column(db.String(50), nullable=False)
    changed_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    source_ip = db.Column(db.String(45))
