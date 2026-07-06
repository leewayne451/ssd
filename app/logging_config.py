"""Logging configuration (NFR-11 observability).

Production gets rotating file handlers under $LOG_DIR — the general app log
plus dedicated audit/security streams that complement the AuditLog and
SecurityEvent database records; debug/testing log to stderr. Sizes and
backup counts are capped so logs cannot fill the disk.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler


def configure_logging(app):
    """Attach environment-appropriate log handlers to `app`."""
    log_level = logging.DEBUG if app.debug else logging.INFO

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
    )

    if not app.debug and not app.testing:
        log_dir = os.environ.get("LOG_DIR", "logs")
        os.makedirs(log_dir, exist_ok=True)

        audit_handler = RotatingFileHandler(
            os.path.join(log_dir, "audit.log"),
            maxBytes=10_000_000,
            backupCount=10,
        )
        audit_handler.setFormatter(formatter)
        audit_handler.setLevel(logging.INFO)

        security_handler = RotatingFileHandler(
            os.path.join(log_dir, "security.log"),
            maxBytes=10_000_000,
            backupCount=10,
        )
        security_handler.setFormatter(formatter)
        security_handler.setLevel(logging.WARNING)

        app.logger.addHandler(audit_handler)

        # Also stream to stdout so `docker logs` / the container platform capture
        # application logs (file handlers alone are invisible outside the volume).
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        stream_handler.setLevel(logging.INFO)
        app.logger.addHandler(stream_handler)

        security_logger = logging.getLogger("security")
        security_logger.addHandler(security_handler)
        security_logger.setLevel(logging.WARNING)

    app.logger.setLevel(log_level)
