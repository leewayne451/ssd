import os
import uuid
from typing import Optional

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def _detect_type_magic(file) -> Optional[str]:
    """Detect basic image type by magic bytes. Returns one of 'png','jpeg','webp' or None."""
    file.seek(0)
    header = file.read(12)
    file.seek(0)

    if len(header) >= 8 and header[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"

    # JPEG files start with 0xFFD8FF
    if len(header) >= 3 and header[0:3] == b"\xff\xd8\xff":
        return "jpeg"

    # WebP: 'RIFF'....'WEBP' at offset 8
    if len(header) >= 12 and header[0:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "webp"

    return None


def validate_upload(file):
    """Validate an uploaded file for extension, size, and magic bytes consistency.

    Returns a list of error messages (empty on success).
    """
    errors = []
    if not file or not getattr(file, "filename", None):
        errors.append("No file provided.")
        return errors

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        errors.append(f"File type .{ext} is not allowed.")

    # Size check
    try:
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
    except Exception:
        size = None

    if size is not None and size > MAX_FILE_SIZE:
        errors.append("File exceeds the 5 MB size limit.")

    # Magic byte check
    detected = _detect_type_magic(file)
    if not detected:
        errors.append("File content type could not be determined or is unsupported.")
    else:
        # Accept jpeg extension variants
        normalized_ext = "jpeg" if ext == "jpg" else ext
        if normalized_ext != detected:
            errors.append(
                f"File extension .{ext} does not match file content ({detected})."
            )

    return errors


def generate_stored_filename(original_filename):
    ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else "bin"
    return f"{uuid.uuid4().hex}.{ext}"
