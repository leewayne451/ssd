import os
import uuid

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def validate_upload(file):
    errors = []
    if not file or not file.filename:
        errors.append("No file provided.")
        return errors

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        errors.append(f"File type .{ext} is not allowed.")

    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    if size > MAX_FILE_SIZE:
        errors.append("File exceeds the 5 MB size limit.")

    return errors


def generate_stored_filename(original_filename):
    ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else "bin"
    return f"{uuid.uuid4().hex}.{ext}"
