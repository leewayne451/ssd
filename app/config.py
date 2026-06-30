"""
Château Collective — Configuration classes

Hierarchy:
  Config (base)
    ├── DevelopmentConfig
    ├── TestingConfig
    └── ProductionConfig

All secrets must come from environment variables — never hardcoded.
python-dotenv loads a .env file automatically when the app starts locally.
"""

import os
from pathlib import Path

# Load .env for local development (no-op if python-dotenv is absent or file missing)
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Resolve the instance folder path relative to this file's grandparent directory
_BASE_DIR = Path(__file__).resolve().parent.parent
_INSTANCE_DIR = _BASE_DIR / "instance"


class Config:
    """Base configuration — shared defaults."""

    # ------------------------------------------------------------------
    # Security defaults
    # ------------------------------------------------------------------
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "Lax"
    # Override per-environment below:
    SESSION_COOKIE_SECURE: bool = False

    SESSION_TIMEOUT_MINUTES: int = 30

    # ------------------------------------------------------------------
    # Secret key — MUST be set via env var in production
    # ------------------------------------------------------------------
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-insecure-placeholder-change-me")

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------
    SQLALCHEMY_DATABASE_URI: str = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{_INSTANCE_DIR / 'chateau.db'}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # ------------------------------------------------------------------
    # General
    # ------------------------------------------------------------------
    DEBUG: bool = False
    TESTING: bool = False


class DevelopmentConfig(Config):
    """Local development — relaxed security so plain HTTP works."""

    DEBUG: bool = True
    SESSION_COOKIE_SECURE: bool = False  # HTTP is fine locally


class TestingConfig(Config):
    """Automated tests — in-memory SQLite, CSRF/cookies disabled for simplicity."""

    TESTING: bool = True
    DEBUG: bool = True

    # Use an in-memory database so tests are always isolated and fast
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///:memory:"

    # Avoid WTF/CSRF complications in tests (no forms yet in Phase 0)
    WTF_CSRF_ENABLED: bool = False

    # Any secret key is fine for testing — never a real value
    SECRET_KEY: str = "test-secret-key-not-for-production"


class ProductionConfig(Config):
    """Production — strict security, no debug, env-var secrets required."""

    SESSION_COOKIE_SECURE: bool = True
    SESSION_COOKIE_SAMESITE: str = "Lax"

    @classmethod
    def validate(cls) -> None:
        """
        Call this at startup to fail loudly if required env vars are missing.
        Phase 1+ should invoke this inside create_app() when config_name=='production'.
        """
        secret = os.environ.get("SECRET_KEY")
        if not secret or secret == "dev-insecure-placeholder-change-me":  # nosec B105
            raise RuntimeError(
                "SECRET_KEY environment variable is not set or is using the "
                "insecure placeholder. Set a strong random value before running "
                "in production."
            )
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            raise RuntimeError(
                "DATABASE_URL environment variable is not set. "
                "Configure a database URI before running in production."
            )


# ------------------------------------------------------------------
# Convenience map used by create_app()
# ------------------------------------------------------------------
config_map: dict[str, type[Config]] = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
