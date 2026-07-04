"""
Regression guard for GitHub Actions workflow policies.

The pipelines are security controls in their own right; these tests keep the
policy expressions from silently regressing in future edits (AI review
finding F2 on PR #70):

  1. CI / Security Scan / DAST / Image Scan must cancel superseded runs on
     PR branches ONLY — runs on main must never be cancelled, so every merge
     commit keeps a complete validation record (D2 evidence).
  2. Deploy must never cancel an in-flight deploy.
  3. Every workflow must declare least-privilege token permissions.
"""
from pathlib import Path

import yaml

WORKFLOWS_DIR = Path(__file__).resolve().parents[2] / ".github" / "workflows"

# Workflows that use per-ref concurrency with conditional cancellation.
CONDITIONAL_CANCEL = {
    "ci.yml",
    "security-scan.yml",
    "dast-zap.yml",
    "image-scan.yml",
}

EXPECTED_CONDITION = "${{ github.ref != 'refs/heads/main' }}"


def _load(name):
    return yaml.safe_load((WORKFLOWS_DIR / name).read_text(encoding="utf-8"))


def test_all_workflows_parse_as_yaml():
    files = sorted(WORKFLOWS_DIR.glob("*.yml"))
    assert files, f"no workflows found under {WORKFLOWS_DIR}"
    for f in files:
        yaml.safe_load(f.read_text(encoding="utf-8"))  # raises on breakage


def test_policy_covered_workflows_exist():
    """Fail with a clear message (not a FileNotFoundError) if a workflow in
    the policy set is renamed/removed without updating this test."""
    actual = {f.name for f in WORKFLOWS_DIR.glob("*.yml")}
    missing = sorted((CONDITIONAL_CANCEL | {"deploy-aws.yml"}) - actual)
    assert not missing, (
        f"policy-covered workflow file(s) not found: {missing} — "
        "if a workflow was renamed, update CONDITIONAL_CANCEL in this test "
        "and any documentation referencing it"
    )


def test_docs_reference_only_real_workflow_files():
    """Anti-drift guard: any *.yml the CI/CD architecture doc mentions must
    actually exist (workflow files under .github/workflows, compose files in
    the repo root)."""
    import re

    repo_root = WORKFLOWS_DIR.parents[1]
    doc = repo_root / "docs" / "architecture" / "ci_cd.md"
    if not doc.exists():  # doc is optional; the guard is not load-bearing
        return
    mentioned = set(re.findall(r"\b[\w.-]+\.ya?ml\b", doc.read_text(encoding="utf-8")))
    search_dirs = [WORKFLOWS_DIR, repo_root, repo_root / "security"]
    missing = sorted(
        name
        for name in mentioned
        if not any((d / name).exists() for d in search_dirs)
    )
    assert not missing, (
        f"docs/architecture/ci_cd.md references non-existent file(s): {missing}"
    )


def test_scan_workflows_never_cancel_runs_on_main():
    for name in sorted(CONDITIONAL_CANCEL):
        wf = _load(name)
        concurrency = wf.get("concurrency")
        assert concurrency, f"{name}: concurrency block removed"
        assert concurrency.get("cancel-in-progress") == EXPECTED_CONDITION, (
            f"{name}: cancel-in-progress must be exactly {EXPECTED_CONDITION!r} "
            "(cancel superseded PR runs; never cancel on main)"
        )


def test_deploy_never_cancels_inflight_deploys():
    wf = _load("deploy-aws.yml")
    concurrency = wf.get("concurrency")
    assert concurrency, "deploy-aws.yml: concurrency block removed"
    assert concurrency.get("cancel-in-progress") is False, (
        "deploy-aws.yml: an in-flight deploy must never be cancelled "
        "(a half-finished deploy leaves the VM in an unknown state)"
    )


def test_every_workflow_declares_token_permissions():
    for f in sorted(WORKFLOWS_DIR.glob("*.yml")):
        wf = yaml.safe_load(f.read_text(encoding="utf-8"))
        assert "permissions" in wf, (
            f"{f.name}: missing top-level 'permissions' — workflows must pin "
            "the GITHUB_TOKEN to least privilege"
        )
