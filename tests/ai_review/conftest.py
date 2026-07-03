"""Shared fixtures for the AI review tooling tests.

These tests never call the real OpenAI or GitHub APIs; everything network-
shaped is mocked or exercised through pure deterministic functions.
"""

import pytest

from tools.ai_review.config import Settings


@pytest.fixture()
def settings() -> Settings:
    return Settings(
        review_model="gpt-5.4-mini",
        triage_model="gpt-5.4-mini",
        audit_model="gpt-5.5",
        max_file_chars=500,
        max_context_chars=2_000,
        max_doc_chars=800,
        max_docs_total_chars=2_000,
        max_scanner_findings=10,
        max_output_tokens=1_000,
        request_timeout_seconds=30,
        max_retries=1,
        max_comment_chars=5_000,
    )
