import os
from pathlib import Path
from typing import Tuple, Optional
from werkzeug.utils import secure_filename
from flask import current_app

from app.security.file_validation import validate_upload, generate_stored_filename

try:
	from app.extensions import db
	from app.models.uploaded_file import UploadedFile
except Exception:
	db = None
	UploadedFile = None


def save_upload(file, listing_id: Optional[int] = None) -> Tuple[bool, list]:
	"""Validate and save an uploaded file.

	Returns (True, metadata_dict) on success or (False, [errors]) on failure.
	"""
	errors = validate_upload(file)
	if errors:
		return False, errors

	original = secure_filename(getattr(file, "filename", ""))
	stored = generate_stored_filename(original)

	# Determine upload directory: prefer app config, fallback to env var or 'uploads'
	upload_dir = current_app.config.get("UPLOAD_DIR") or os.environ.get("UPLOAD_DIR", "uploads")
	# Store uploads under the instance folder to avoid serving them directly from static
	dest_root = Path(current_app.instance_path) / upload_dir
	dest_root.mkdir(parents=True, exist_ok=True)

	dest_path = dest_root / stored

	# Save file stream to destination
	file.seek(0)
	with open(dest_path, "wb") as fh:
		# file may be a Werkzeug FileStorage with .stream
		stream = getattr(file, "stream", file)
		stream.seek(0)
		while True:
			chunk = stream.read(8192)
			if not chunk:
				break
			fh.write(chunk)

	# Set conservative permissions where supported. If this fails (e.g. on
	# platforms that don't support chmod or due to permission issues), log a
	# warning rather than silently swallowing the error.
	try:
		os.chmod(dest_path, 0o640)
	except OSError as exc:
		current_app.logger.warning(
			"Failed to set permissions on uploaded file %s: %s",
			str(dest_path),
			exc,
		)

	metadata = {
		"original_filename": original,
		"stored_filename": stored,
		"mime_type": None,
		"file_size": dest_path.stat().st_size,
		"path": str(dest_path),
	}

	# If we have the UploadedFile model, create a DB record
	if UploadedFile is not None and db is not None:
		uf = UploadedFile(
			listing_id=listing_id or 0,
			original_filename=original,
			stored_filename=stored,
			mime_type=metadata["mime_type"] or "application/octet-stream",
			file_size=metadata["file_size"],
		)
		db.session.add(uf)
		db.session.commit()
		metadata["id"] = uf.id

	return True, metadata

