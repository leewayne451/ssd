"""Uploaded listing image metadata (SDR-04)."""

from app.extensions import db


class UploadedFile(db.Model):
    """Metadata for a validated listing image (SDR-04). stored_filename is
    always server-generated (uuid + allow-listed extension) — user-supplied
    names never reach the filesystem.
    """
    __tablename__ = "uploaded_files"

    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey("product_listings.id"), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), unique=True, nullable=False)
    mime_type = db.Column(db.String(50), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    uploaded_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
