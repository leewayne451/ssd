from app.extensions import db


class Cart(db.Model):
    __tablename__ = "carts"

    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now(), onupdate=db.func.now())

    items = db.relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")
