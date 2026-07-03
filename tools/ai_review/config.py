"""Configuration for the AI review tooling.

All limits are read from environment variables with safe, bounded defaults.
Model names come from the repository variables AI_REVIEW_MODEL,
AI_TRIAGE_MODEL and AI_AUDIT_MODEL.

OPENAI_API_KEY is intentionally never read, stored or printed here; only the
official OpenAI SDK client reads it from the environment.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

DEFAULT_REVIEW_MODEL = "gpt-5.4-mini"
DEFAULT_TRIAGE_MODEL = "gpt-5.4-mini"
DEFAULT_AUDIT_MODEL = "gpt-5.5"

# Models that the manually dispatched milestone audit may use.
ALLOWED_AUDIT_MODELS = ("gpt-5.5", "gpt-5.4-mini")

# Allowed milestone-audit scopes (validated workflow_dispatch input).
ALLOWED_AUDIT_SCOPES = ("full", "security", "requirements", "architecture", "tests")


def _int_env(name: str, default: int, minimum: int, maximum: int) -> int:
    """Read an integer env var, clamped to [minimum, maximum]."""
    raw = os.environ.get(name, "")
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(maximum, value))


def _model_env(name: str, default: str) -> str:
    value = os.environ.get(name, "").strip()
    return value or default


@dataclass(frozen=True)
class Settings:
    """Bounded runtime settings for one AI tooling invocation."""

    review_model: str = field(default="")
    triage_model: str = field(default="")
    audit_model: str = field(default="")

    # Input bounds (characters).
    max_file_chars: int = 0
    max_context_chars: int = 0
    max_doc_chars: int = 0
    max_docs_total_chars: int = 0
    max_scanner_findings: int = 0

    # Request bounds.
    max_output_tokens: int = 0
    request_timeout_seconds: int = 0
    max_retries: int = 0

    # Rendering bounds.
    max_comment_chars: int = 0

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            review_model=_model_env("AI_REVIEW_MODEL", DEFAULT_REVIEW_MODEL),
            triage_model=_model_env("AI_TRIAGE_MODEL", DEFAULT_TRIAGE_MODEL),
            audit_model=_model_env("AI_AUDIT_MODEL", DEFAULT_AUDIT_MODEL),
            max_file_chars=_int_env("AI_MAX_FILE_CHARS", 12_000, 500, 60_000),
            max_context_chars=_int_env("AI_MAX_CONTEXT_CHARS", 90_000, 2_000, 400_000),
            max_doc_chars=_int_env("AI_MAX_DOC_CHARS", 15_000, 500, 80_000),
            max_docs_total_chars=_int_env(
                "AI_MAX_DOCS_TOTAL_CHARS", 60_000, 1_000, 300_000
            ),
            max_scanner_findings=_int_env("AI_MAX_SCANNER_FINDINGS", 120, 5, 1_000),
            max_output_tokens=_int_env("AI_MAX_OUTPUT_TOKENS", 6_000, 256, 32_000),
            request_timeout_seconds=_int_env("AI_REQUEST_TIMEOUT_SECONDS", 180, 10, 600),
            max_retries=_int_env("AI_MAX_RETRIES", 2, 0, 5),
            # GitHub caps issue comments at 65536 characters; leave headroom.
            max_comment_chars=_int_env("AI_MAX_COMMENT_CHARS", 60_000, 2_000, 65_000),
        )
