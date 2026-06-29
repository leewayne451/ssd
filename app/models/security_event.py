from app.extensions import db


class SecurityEvent(db.Model):
    __tablename__ = "security_events"

    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(100), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    source_ip = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now(), index=True)
