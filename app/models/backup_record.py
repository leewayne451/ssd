"""Backup snapshot metadata entity (M12)."""

from app.extensions import db


class BackupRecord(db.Model):
    """Metadata for a database snapshot created by backup_service (M12,
    NFR-03/FSR-25): server-generated filename, size, type, acting admin.
    """
    __tablename__ = "backup_records"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer)
    backup_type = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    created_by_admin_id = db.Column(db.Integer, db.ForeignKey("users.id"))
