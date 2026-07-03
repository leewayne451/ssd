"""Single-comment upsert against the GitHub REST API.

Endpoints are built exclusively from a validated ``owner/repo`` slug and a
validated integer PR number. Model output is never used to construct URLs,
parameters or headers.
"""

from __future__ import annotations

import os
import re

import requests

_API_ROOT = "https://api.github.com"
_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_TIMEOUT = 30


class GitHubCommentError(RuntimeError):
    pass


def _validate(repo: str, pr_number: int) -> tuple[str, int]:
    if not _REPO_RE.match(repo or ""):
        raise GitHubCommentError("invalid repository slug")
    number = int(pr_number)
    if number <= 0:
        raise GitHubCommentError("invalid pull request number")
    return repo, number


def _headers(token: str) -> dict[str, str]:
    if not token:
        raise GitHubCommentError("missing GitHub token")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def find_marked_comment(
    repo: str, pr_number: int, marker: str, token: str
) -> int | None:
    """Return the id of the existing comment carrying the marker, if any."""
    repo, number = _validate(repo, pr_number)
    headers = _headers(token)
    page = 1
    while page <= 20:  # bounded pagination
        response = requests.get(
            f"{_API_ROOT}/repos/{repo}/issues/{number}/comments",
            headers=headers,
            params={"per_page": 100, "page": page},
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
        comments = response.json()
        if not comments:
            return None
        for comment in comments:
            if marker in (comment.get("body") or ""):
                return int(comment["id"])
        page += 1
    return None


def upsert_comment(
    repo: str,
    pr_number: int,
    marker: str,
    body: str,
    token: str | None = None,
) -> str:
    """Create or update the single conversation comment for this workflow.

    Returns "created" or "updated". The marker must already be embedded in
    the rendered body (render.py includes it).
    """
    token = token if token is not None else os.environ.get("GITHUB_TOKEN", "")
    repo, number = _validate(repo, pr_number)
    if marker not in body:
        raise GitHubCommentError("rendered body is missing its stable marker")

    existing = find_marked_comment(repo, number, marker, token)
    headers = _headers(token)
    if existing is not None:
        response = requests.patch(
            f"{_API_ROOT}/repos/{repo}/issues/comments/{int(existing)}",
            headers=headers,
            json={"body": body},
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
        return "updated"
    response = requests.post(
        f"{_API_ROOT}/repos/{repo}/issues/{number}/comments",
        headers=headers,
        json={"body": body},
        timeout=_TIMEOUT,
    )
    response.raise_for_status()
    return "created"
