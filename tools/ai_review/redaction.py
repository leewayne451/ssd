"""Secret redaction for text that is about to leave the runner or be rendered.

This is a defence-in-depth layer. The primary control is sensitive-path
exclusion in path_filter.py; redaction only catches secret-shaped strings
that slip into otherwise reviewable text (diffs, scanner messages, docs).
"""

from __future__ import annotations

import re

_REPLACEMENT = "[REDACTED:{label}]"

# Order matters: multi-line PEM blocks first, then specific token formats,
# then generic assignments.
_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "private-key",
        re.compile(
            r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?"
            r"(?:-----END [A-Z0-9 ]*PRIVATE KEY-----|\Z)",
            re.DOTALL,
        ),
    ),
    # OpenAI keys (sk-..., sk-proj-...)
    ("openai-key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{16,}\b")),
    # GitHub tokens
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("github-token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    # AWS access key ids and secret keys
    ("aws-access-key", re.compile(r"\b(?:AKIA|ASIA|AGPA|AIDA|AROA|ANPA)[0-9A-Z]{16}\b")),
    (
        "aws-secret-key",
        re.compile(
            r"(?i)\baws(?:_|-)?secret(?:_|-)?(?:access(?:_|-)?)?key\b"
            r"\s*[:=]\s*[\"']?[A-Za-z0-9/+=]{30,}[\"']?"
        ),
    ),
    # Bearer tokens in headers or code
    ("bearer-token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{16,}")),
    # JWT-shaped strings
    (
        "jwt",
        re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
    ),
    # Generic credential assignments: password=..., secret=..., token=..., api_key=...
    (
        "credential-assignment",
        re.compile(
            r"(?i)\b(password|passwd|pwd|secret|secret_key|token|auth_token"
            r"|api[_-]?key|access[_-]?key|private[_-]?key|client[_-]?secret)\b"
            r"(\s*[:=]\s*|\s*[:=]>\s*)"
            r"[\"']?[^\s\"',;]{4,}[\"']?"
        ),
    ),
)


def redact(text: str) -> str:
    """Return text with secret-shaped substrings replaced by stable markers."""
    if not text:
        return text
    result = text
    for label, pattern in _PATTERNS:
        if label == "credential-assignment":
            # Keep the key name so reviewers can still see what was set.
            result = pattern.sub(
                lambda m: f"{m.group(1)}{m.group(2)}"
                + _REPLACEMENT.format(label="credential"),
                result,
            )
        else:
            result = pattern.sub(_REPLACEMENT.format(label=label), result)
    return result


def contains_secret(text: str) -> bool:
    """True when the text still matches any known secret pattern."""
    return any(pattern.search(text) for _, pattern in _PATTERNS)
