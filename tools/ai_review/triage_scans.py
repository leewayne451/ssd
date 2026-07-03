"""Orchestrator for conditional AI scanner triage (Phase 7).

Parses Bandit/Semgrep (and optionally pip-audit) reports locally, skips the
OpenAI API entirely when there are no findings, and never suppresses, alters
or resolves any scanner result. Output is advisory Markdown only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .config import Settings
from .github_comment import upsert_comment
from .openai_client import run_structured_request
from .redaction import redact
from .render import TRIAGE_MARKER, RenderMeta, render_triage
from .review_pr import parse_pr_number
from .scanner_parser import (
    ParsedReport,
    ScannerFinding,
    collect_findings,
    parse_bandit,
    parse_pip_audit,
    parse_semgrep,
)
from .schemas import TriageResponse, strict_json_schema, validate_response

_PROMPT_PATH = Path(__file__).parent / "prompts" / "scan_triage.md"


def should_call_api(findings: list[ScannerFinding]) -> bool:
    """The OpenAI API is only used when there is something to triage."""
    return len(findings) > 0


def _findings_payload(findings: list[ScannerFinding], settings: Settings) -> tuple[str, bool]:
    """Serialise findings for the model, bounded and redacted."""
    truncated = False
    bounded = findings
    if len(bounded) > settings.max_scanner_findings:
        bounded = bounded[: settings.max_scanner_findings]
        truncated = True
    payload = [
        {
            "finding_id": f.finding_id,
            "scanner": f.scanner,
            "rule_id": f.rule_id,
            "severity": f.severity,
            "path": f.path,
            "line": f.line,
            "message": redact(f.message),
            "group_key": f.group_key,
        }
        for f in bounded
    ]
    return json.dumps(payload, indent=1), truncated


def build_user_content(findings_json: str, report_errors: list[str]) -> str:
    errors_text = "\n".join(f"- {e}" for e in report_errors) or "- none"
    return (
        "<TRUSTED_PROJECT_CONTEXT>\n"
        "Project: Chateau Collective (Flask luxury-goods marketplace, see "
        "system prompt for the security model).\n"
        f"Report parsing issues:\n{errors_text}\n"
        "</TRUSTED_PROJECT_CONTEXT>\n\n"
        "<UNTRUSTED_SCANNER_REPORT>\n"
        f"{findings_json}\n"
        "</UNTRUSTED_SCANNER_REPORT>\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AI scanner triage")
    parser.add_argument("--bandit", type=Path, default=None)
    parser.add_argument("--semgrep", type=Path, default=None)
    parser.add_argument("--pip-audit", dest="pip_audit", type=Path, default=None)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pr-number", default=os.environ.get("PR_NUMBER") or None)
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"))
    args = parser.parse_args(argv)

    settings = Settings.from_env()

    reports: list[ParsedReport] = []
    if args.bandit:
        reports.append(parse_bandit(args.bandit))
    if args.semgrep:
        reports.append(parse_semgrep(args.semgrep))
    if args.pip_audit:
        reports.append(parse_pip_audit(args.pip_audit))
    errors = [e for r in reports for e in r.errors]
    findings = collect_findings(reports)

    response = None
    meta = RenderMeta(model="none (no findings)", truncated=False)
    if should_call_api(findings):
        findings_json, truncated = _findings_payload(findings, settings)
        result = run_structured_request(
            model=settings.triage_model,
            system_prompt=_PROMPT_PATH.read_text(encoding="utf-8"),
            user_content=build_user_content(findings_json, errors),
            schema_name="triage_response",
            json_schema=strict_json_schema(TriageResponse),
            settings=settings,
        )
        response = validate_response(TriageResponse, result.data)
        meta = RenderMeta(
            model=result.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            truncated=truncated,
        )
    else:
        print("No scanner findings; skipping the OpenAI API entirely.")

    body = render_triage(findings, response, meta, settings)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(body, encoding="utf-8")
    print(f"Triage report written to {args.output}")

    if args.pr_number:
        try:
            pr_number = parse_pr_number(str(args.pr_number))
        except ValueError as exc:
            print(f"::error::{exc}", file=sys.stderr)
            return 1
        outcome = upsert_comment(
            args.repo or "",
            pr_number,
            TRIAGE_MARKER,
            body,
            os.environ.get("GITHUB_TOKEN", ""),
        )
        print(f"Triage comment {outcome} on PR #{pr_number}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
