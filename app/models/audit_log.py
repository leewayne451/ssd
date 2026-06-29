from app.extensions import db


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    actor_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    action_type = db.Column(db.String(100), nullable=False, index=True)
    target_type = db.Column(db.String(50))
    target_id = db.Column(db.Integer)
    details = db.Column(db.Text)
    source_ip = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now(), index=True)
