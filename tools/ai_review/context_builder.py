"""Bounded context construction for AI review calls.

Selects relevant diffs (highest security priority first), enforces per-file
and total character limits, preserves filenames, and marks the context as
truncated whenever anything was cut. Truncated content is explicitly labelled
so the model is never told it reviewed content that was dropped.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import Settings
from .path_filter import PathDecision, filter_paths
from .redaction import redact

_TRUNCATION_NOTE = "[TRUNCATED: remainder of this file was NOT reviewed]"
_OMITTED_NOTE = "[OMITTED: the following files were NOT reviewed (context limit)]"


@dataclass(frozen=True)
class FileDiff:
    """One changed file and its unified diff patch, treated as untrusted data."""

    path: str
    patch: str


@dataclass
class DiffContext:
    text: str = ""
    included_files: list[str] = field(default_factory=list)
    truncated_files: list[str] = field(default_factory=list)
    omitted_files: list[str] = field(default_factory=list)
    excluded: list[PathDecision] = field(default_factory=list)
    truncated: bool = False

    @property
    def has_content(self) -> bool:
        return bool(self.included_files)


def build_diff_context(diffs: list[FileDiff], settings: Settings) -> DiffContext:
    """Build the bounded, redacted diff context for a single model call."""
    by_path = {d.path.replace("\\", "/"): d for d in diffs}
    included, excluded = filter_paths(list(by_path.keys()))

    ctx = DiffContext(excluded=excluded)
    sections: list[str] = []
    used = 0

    for decision in included:
        diff = by_path[decision.path]
        header = f"--- FILE: {decision.path} (priority {decision.priority}) ---\n"
        budget_left = settings.max_context_chars - used - len(header)
        if budget_left <= 200:
            ctx.omitted_files.append(decision.path)
            ctx.truncated = True
            continue

        body = redact(diff.patch or "")
        if len(body) > settings.max_file_chars:
            body = body[: settings.max_file_chars] + "\n" + _TRUNCATION_NOTE
            ctx.truncated_files.append(decision.path)
            ctx.truncated = True
        if len(body) > budget_left:
            body = body[:budget_left] + "\n" + _TRUNCATION_NOTE
            if decision.path not in ctx.truncated_files:
                ctx.truncated_files.append(decision.path)
            ctx.truncated = True

        section = header + body + "\n"
        sections.append(section)
        used += len(section)
        ctx.included_files.append(decision.path)

    if ctx.omitted_files:
        # Keep the omission note itself bounded so it cannot blow the budget.
        names = ", ".join(ctx.omitted_files)
        if len(names) > 300:
            names = names[:300] + "..."
        sections.append(
            f"{_OMITTED_NOTE}\n{len(ctx.omitted_files)} file(s) omitted: {names}\n"
        )
    ctx.text = "".join(sections)
    return ctx
