"""Orchestrator for the contextual PR review (Phase 5).

Runs from trusted default-branch code only. The PR diff is fetched through
the GitHub API strictly as text and never checked out, imported or executed.
Makes at most one model call per run.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import requests

from .config import Settings
from .context_builder import FileDiff, build_diff_context
from .document_loader import load_documents
from .github_comment import upsert_comment
from .openai_client import run_structured_request
from .render import PR_REVIEW_MARKER, RenderMeta, render_pr_review
from .schemas import PRReviewResponse, strict_json_schema, validate_response

_API_ROOT = "https://api.github.com"
_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_TIMEOUT = 30
_PROMPT_PATH = Path(__file__).parent / "prompts" / "pr_review.md"


def parse_pr_number(raw: str | None) -> int:
    """Validate an externally supplied PR number (must be a positive int)."""
    if raw is None or not re.fullmatch(r"[0-9]{1,9}", raw.strip()):
        raise ValueError("PR number must be a positive integer")
    number = int(raw.strip())
    if number <= 0:
        raise ValueError("PR number must be a positive integer")
    return number


def is_same_repo_pr(pr_json: dict) -> bool:
    """True only when the PR head lives in the base repository (not a fork).

    Fork PRs are skipped by default so the API key is never spent on -- or
    exposed to workflows triggered by -- untrusted external activity.
    """
    head_repo = ((pr_json.get("head") or {}).get("repo") or {}).get("full_name")
    base_repo = ((pr_json.get("base") or {}).get("repo") or {}).get("full_name")
    return bool(head_repo) and head_repo == base_repo


def resolve_pr_for_commit(pulls_payload: list, base_repo: str) -> int | None:
    """Pick the open same-repository PR associated with a commit, if any."""
    for pr in pulls_payload or []:
        if not isinstance(pr, dict):
            continue
        if pr.get("state") != "open":
            continue
        if ((pr.get("base") or {}).get("repo") or {}).get("full_name") != base_repo:
            continue
        if not is_same_repo_pr(pr):
            continue
        number = pr.get("number")
        if isinstance(number, int) and number > 0:
            return number
    return None


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def fetch_pr(repo: str, pr_number: int, token: str) -> dict:
    response = requests.get(
        f"{_API_ROOT}/repos/{repo}/pulls/{int(pr_number)}",
        headers=_headers(token),
        timeout=_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def fetch_pr_files(repo: str, pr_number: int, token: str) -> list[FileDiff]:
    """Fetch changed filenames and unified diffs as data (never executed)."""
    diffs: list[FileDiff] = []
    page = 1
    while page <= 10:  # bounded pagination (up to 1000 files)
        response = requests.get(
            f"{_API_ROOT}/repos/{repo}/pulls/{int(pr_number)}/files",
            headers=_headers(token),
            params={"per_page": 100, "page": page},
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
        batch = response.json()
        if not batch:
            break
        for item in batch:
            diffs.append(
                FileDiff(
                    path=str(item.get("filename", "")),
                    patch=str(item.get("patch") or ""),
                )
            )
        page += 1
    return diffs


def list_existing_tests(repo_root: Path, limit: int = 300) -> list[str]:
    """Bounded listing of existing test files (paths only, no content).

    Lets the model check suggested tests against what already exists instead
    of proposing duplicates.
    """
    tests_dir = repo_root / "tests"
    if not tests_dir.is_dir():
        return []
    paths = sorted(
        p.relative_to(repo_root).as_posix()
        for p in tests_dir.rglob("test_*.py")
    )
    return paths[:limit]


def build_user_content(
    doc_text: str,
    diff_text: str,
    pr_number: int,
    changed_count: int,
    test_files: list[str] | None = None,
) -> str:
    """Compose the model input with explicit trust boundaries."""
    tests_text = ""
    if test_files:
        tests_text = (
            "Existing test files (paths only; use these to judge test gaps):\n"
            + "\n".join(f"- {path}" for path in test_files)
            + "\n\n"
        )
    return (
        "<TRUSTED_PROJECT_CONTEXT>\n"
        f"Pull request number: {pr_number}\n"
        f"Changed files considered: {changed_count}\n\n"
        f"{tests_text}"
        f"{doc_text}"
        "</TRUSTED_PROJECT_CONTEXT>\n\n"
        "<UNTRUSTED_PR_DIFF>\n"
        f"{diff_text}"
        "</UNTRUSTED_PR_DIFF>\n"
    )


def _skip_comment(reason: str) -> str:
    return (
        f"{PR_REVIEW_MARKER}\n"
        "## AI Contextual PR Review\n\n"
        f"**Skipped:** {reason}\n\n"
        "_No AI model call was made for this run._\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AI contextual PR review")
    parser.add_argument("--pr-number", default=os.environ.get("PR_NUMBER"))
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"))
    args = parser.parse_args(argv)

    settings = Settings.from_env()
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = args.repo or ""
    if not _REPO_RE.match(repo):
        print("::error::invalid or missing repository slug", file=sys.stderr)
        return 1
    try:
        pr_number = parse_pr_number(args.pr_number)
    except ValueError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1

    pr_json = fetch_pr(repo, pr_number, token)
    if not is_same_repo_pr(pr_json):
        print("Fork or cross-repository PR detected; skipping AI review.")
        return 0
    if pr_json.get("state") != "open":
        print("PR is not open; skipping AI review.")
        return 0

    diffs = fetch_pr_files(repo, pr_number, token)
    diff_ctx = build_diff_context(diffs, settings)
    if not diff_ctx.has_content:
        print("No relevant reviewable changes; no AI call made.")
        upsert_comment(
            repo,
            pr_number,
            PR_REVIEW_MARKER,
            _skip_comment(
                "no relevant reviewable files in this PR (only excluded, "
                "generated or non-security-relevant paths changed)."
            ),
            token,
        )
        return 0

    repo_root = Path(__file__).resolve().parents[2]
    doc_ctx = load_documents(
        manifest_path=Path(__file__).parent / "document_manifest.yml",
        repo_root=repo_root,
        settings=settings,
        purpose="pr_review",
        changed_paths=diff_ctx.included_files,
    )

    system_prompt = _PROMPT_PATH.read_text(encoding="utf-8")
    user_content = build_user_content(
        doc_ctx.as_text(),
        diff_ctx.text,
        pr_number,
        len(diff_ctx.included_files),
        test_files=list_existing_tests(repo_root),
    )

    result = run_structured_request(
        model=settings.review_model,
        system_prompt=system_prompt,
        user_content=user_content,
        schema_name="pr_review_response",
        json_schema=strict_json_schema(PRReviewResponse),
        settings=settings,
    )
    response = validate_response(PRReviewResponse, result.data)

    meta = RenderMeta(
        model=result.model,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        truncated=diff_ctx.truncated or doc_ctx.truncated,
    )
    body = render_pr_review(response, meta, settings)
    outcome = upsert_comment(repo, pr_number, PR_REVIEW_MARKER, body, token)
    print(f"Review comment {outcome} on PR #{pr_number}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
