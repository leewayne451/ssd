"""Deny-first path filtering for content sent to the OpenAI API.

Sensitive and generated paths are excluded before any other processing.
Redaction (see redaction.py) is a secondary safety net only -- exclusion
here is the primary control.
"""

from __future__ import annotations

import fnmatch
import posixpath
from dataclasses import dataclass

# Paths that must NEVER be sent to the API, matched deny-first.
# Patterns match either the full path or any individual path segment.
DENY_PATTERNS: tuple[str, ...] = (
    # Environment and secret material
    ".env",
    ".env.*",
    "*.pem",
    "*.ppk",
    "*.key",
    "*.p12",
    "*.pfx",
    "*.crt",
    "*.cer",
    "*.jks",
    "*.keystore",
    "id_rsa*",
    "id_ecdsa*",
    "id_ed25519*",
    "*.pub",
    ".ssh",
    ".aws",
    ".netrc",
    ".git-credentials",
    "*credentials*",
    "secrets.*",
    # Databases and runtime state
    "instance",
    "*.db",
    "*.sqlite",
    "*.sqlite3",
    "*.sqlite-journal",
    "*.sql",
    # User content, logs, backups, audit/security evidence
    "uploads",
    "uploaded_files",
    "backups",
    "backup",
    "logs",
    "*.log",
    "audit*.jsonl",
    # Environments, caches, build output
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    "*.pyc",
    "*.pyo",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".coverage",
    ".coverage.*",
    "htmlcov",
    "dist",
    "build",
    "*.egg-info",
    ".git",
    ".idea",
    ".vscode",
    # Binary and compiled content
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.ico",
    "*.webp",
    "*.svg",
    "*.pdf",
    "*.zip",
    "*.tar",
    "*.gz",
    "*.7z",
    "*.exe",
    "*.dll",
    "*.so",
    "*.dylib",
    "*.whl",
    "*.woff",
    "*.woff2",
    "*.ttf",
    "*.lock",
    "uv.lock",
)

# Files that are reviewable but carry no security signal on their own.
SKIP_PATTERNS: tuple[str, ...] = (
    "*.css",
    "*.scss",
    "*.map",
    ".gitkeep",
    ".gitignore",
    ".gitattributes",
)

# Higher number = reviewed first and kept longest under truncation.
_PRIORITY_RULES: tuple[tuple[str, int], ...] = (
    ("app/security/*", 100),
    ("app/web/routes/*", 90),
    ("app/services/*", 85),
    ("app/web/forms/*", 80),
    ("app/models/*", 75),
    (".github/workflows/*", 72),
    ("app/utils/*", 70),
    ("app/config.py", 70),
    ("app/extensions.py", 70),
    ("app/logging_config.py", 70),
    ("deploy/*", 65),
    ("security/*", 65),
    ("migrations/*", 55),
    ("tests/*", 50),
    ("app/web/templates/*", 45),
    ("requirements*.txt", 45),
    ("tools/*", 40),
    ("app/*", 40),
    ("*.py", 35),
    ("*.yml", 30),
    ("*.yaml", 30),
    ("*.toml", 25),
    ("*.cfg", 25),
    ("*.ini", 25),
    ("*.conf", 25),
    ("*.service", 25),
    ("*.sh", 25),
    ("*.js", 20),
    ("*.html", 20),
    ("*.md", 10),
    ("*.txt", 10),
)


@dataclass(frozen=True)
class PathDecision:
    path: str
    included: bool
    reason: str
    priority: int = 0


def _normalise(path: str) -> str:
    norm = posixpath.normpath(path.replace("\\", "/"))
    # normpath already collapses "./x" to "x"; never strip leading dots from
    # dotfiles such as ".env" or ".coverage".
    return norm.removeprefix("./")


def _matches(path: str, pattern: str) -> bool:
    """Match against the full path, any suffix of it, or any single segment."""
    if fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(path, f"*/{pattern}"):
        return True
    return any(fnmatch.fnmatch(part, pattern) for part in path.split("/"))


def is_denied(path: str) -> bool:
    """True when the path must never leave the runner (deny-first check)."""
    norm = _normalise(path)
    return any(_matches(norm, pattern) for pattern in DENY_PATTERNS)


def _priority(path: str) -> int:
    for pattern, score in _PRIORITY_RULES:
        if fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(path, f"{pattern}*"):
            return score
    return 0


def decide(path: str) -> PathDecision:
    """Classify one changed file. Deny rules always win."""
    norm = _normalise(path)
    if is_denied(norm):
        return PathDecision(norm, False, "sensitive_or_generated")
    if any(_matches(norm, pattern) for pattern in SKIP_PATTERNS):
        return PathDecision(norm, False, "not_relevant")
    priority = _priority(norm)
    if priority <= 0:
        return PathDecision(norm, False, "not_relevant")
    return PathDecision(norm, True, "relevant", priority)


def filter_paths(paths: list[str]) -> tuple[list[PathDecision], list[PathDecision]]:
    """Split changed paths into (included sorted by priority desc, excluded)."""
    included: list[PathDecision] = []
    excluded: list[PathDecision] = []
    for path in paths:
        decision = decide(path)
        (included if decision.included else excluded).append(decision)
    included.sort(key=lambda d: (-d.priority, d.path))
    return included, excluded
