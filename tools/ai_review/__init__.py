"""Shared deterministic tooling for the advisory AI review workflows.

This package is CI-only. It is never imported by the Flask application and
never executes model output. All OpenAI responses are treated as untrusted
data: they are schema-validated, redacted, and rendered to Markdown locally.
"""

__all__ = [
    "config",
    "schemas",
    "path_filter",
    "redaction",
    "context_builder",
    "document_loader",
    "scanner_parser",
    "openai_client",
    "render",
    "github_comment",
]
