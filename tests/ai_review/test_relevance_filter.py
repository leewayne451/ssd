"""Workflow-related helper logic: PR resolution, fork policy, API-skip paths.

No test here performs any network call; orchestrator entry points run with
all remote interactions monkeypatched.
"""

import pytest

from tools.ai_review import review_pr, triage_scans
from tools.ai_review.context_builder import FileDiff
from tools.ai_review.review_pr import (
    is_same_repo_pr,
    parse_pr_number,
    resolve_pr_for_commit,
)

BASE_REPO = "leewayne451/ICT2216_Secure-Software-Development"


def _pr(number=7, state="open", head_repo=BASE_REPO, base_repo=BASE_REPO):
    return {
        "number": number,
        "state": state,
        "head": {"repo": {"full_name": head_repo}},
        "base": {"repo": {"full_name": base_repo}},
    }


class TestPRResolution:
    def test_associated_pr_resolved(self):
        payload = [_pr(number=12)]
        assert resolve_pr_for_commit(payload, BASE_REPO) == 12

    def test_closed_prs_ignored(self):
        assert resolve_pr_for_commit([_pr(state="closed")], BASE_REPO) is None

    def test_no_associated_pr(self):
        assert resolve_pr_for_commit([], BASE_REPO) is None
        assert resolve_pr_for_commit([{"weird": "shape"}], BASE_REPO) is None

    def test_same_repository_pr_allowed(self):
        assert is_same_repo_pr(_pr())

    def test_fork_pr_skipped_by_default(self):
        fork = _pr(head_repo="attacker/ICT2216_Secure-Software-Development")
        assert not is_same_repo_pr(fork)
        assert resolve_pr_for_commit([fork], BASE_REPO) is None

    def test_missing_head_repo_treated_as_fork(self):
        pr = _pr()
        pr["head"]["repo"] = None
        assert not is_same_repo_pr(pr)


class TestPRNumberValidation:
    def test_valid_number(self):
        assert parse_pr_number("42") == 42

    @pytest.mark.parametrize("raw", [None, "", "abc", "-1", "0", "1; rm -rf /"])
    def test_invalid_numbers_rejected(self, raw):
        with pytest.raises(ValueError):
            parse_pr_number(raw)


class TestExistingTestListing:
    def test_lists_test_files_bounded(self, tmp_path):
        tests_dir = tmp_path / "tests" / "unit"
        tests_dir.mkdir(parents=True)
        (tests_dir / "test_auth.py").write_text("def test_x(): pass\n")
        (tests_dir / "helper.py").write_text("# not a test file\n")
        listing = review_pr.list_existing_tests(tmp_path, limit=10)
        assert listing == ["tests/unit/test_auth.py"]

    def test_missing_tests_directory(self, tmp_path):
        assert review_pr.list_existing_tests(tmp_path) == []

    def test_limit_applied(self, tmp_path):
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        for i in range(5):
            (tests_dir / f"test_{i}.py").write_text("pass\n")
        assert len(review_pr.list_existing_tests(tmp_path, limit=3)) == 3


class _Bomb:
    """Fails the test if the OpenAI client is ever invoked."""

    def __call__(self, *args, **kwargs):
        raise AssertionError("OpenAI API must not be called in this scenario")


class TestNoApiCallPaths:
    def test_no_relevant_files_causes_no_api_call(self, monkeypatch, capsys):
        monkeypatch.setattr(review_pr, "run_structured_request", _Bomb())
        monkeypatch.setattr(review_pr, "fetch_pr", lambda *a: _pr())
        monkeypatch.setattr(
            review_pr,
            "fetch_pr_files",
            lambda *a: [FileDiff("app/web/static/css/main.css", "+body{}")],
        )
        recorded = {}

        def fake_upsert(repo, number, marker, body, token):
            recorded["body"] = body
            return "created"

        monkeypatch.setattr(review_pr, "upsert_comment", fake_upsert)
        monkeypatch.setenv("GITHUB_TOKEN", "dummy")
        exit_code = review_pr.main(["--pr-number", "7", "--repo", BASE_REPO])
        assert exit_code == 0
        assert "no ai call" in capsys.readouterr().out.lower()
        assert "Skipped" in recorded["body"]

    def test_fork_pr_skips_before_any_fetch(self, monkeypatch):
        monkeypatch.setattr(review_pr, "run_structured_request", _Bomb())
        monkeypatch.setattr(
            review_pr, "fetch_pr", lambda *a: _pr(head_repo="attacker/fork")
        )
        monkeypatch.setattr(review_pr, "fetch_pr_files", _Bomb())
        monkeypatch.setattr(review_pr, "upsert_comment", _Bomb())
        assert review_pr.main(["--pr-number", "7", "--repo", BASE_REPO]) == 0

    def test_no_scanner_findings_causes_no_api_call(
        self, monkeypatch, tmp_path, capsys
    ):
        monkeypatch.setattr(triage_scans, "run_structured_request", _Bomb())
        output = tmp_path / "triage.md"
        exit_code = triage_scans.main(["--output", str(output)])
        assert exit_code == 0
        assert "skipping the OpenAI API" in capsys.readouterr().out
        assert "No scanner findings" in output.read_text(encoding="utf-8")

    def test_should_call_api_only_with_findings(self):
        assert not triage_scans.should_call_api([])
