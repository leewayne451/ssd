import logging
import os
from logging.handlers import RotatingFileHandler


def configure_logging(app):
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

        security_logger = logging.getLogger("security")
        security_logger.addHandler(security_handler)
        security_logger.setLevel(logging.WARNING)

    app.logger.setLevel(log_level)
