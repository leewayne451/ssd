from app.extensions import db


class CartItem(db.Model):
    __tablename__ = "cart_items"

    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey("carts.id"), nullable=False)
    listing_id = db.Column(db.Integer, db.ForeignKey("product_listings.id"), nullable=False)
    added_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())

    cart = db.relationship("Cart", back_populates="items")
