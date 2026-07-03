"""Parsers for deterministic scanner reports (Bandit, Semgrep, pip-audit).

Every original scanner finding is preserved. Duplicate grouping only adds a
group key; it never deletes or merges away findings. Scanner reports are
untrusted data -- nothing in them is executed or interpolated into commands.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ScannerFinding:
    scanner: str
    rule_id: str
    severity: str
    path: str
    line: int
    message: str
    finding_id: str = ""
    group_key: str = ""

    def __post_init__(self) -> None:
        if not self.group_key:
            self.group_key = f"{self.scanner}:{self.rule_id}:{self.path}"


@dataclass
class ParsedReport:
    scanner: str
    findings: list[ScannerFinding] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _load_json(path: Path, scanner: str) -> tuple[object | None, list[str]]:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return None, [f"{scanner}: report not found: {path.name}"]
    except OSError as exc:
        return None, [f"{scanner}: report unreadable: {type(exc).__name__}"]
    try:
        return json.loads(raw), []
    except json.JSONDecodeError as exc:
        return None, [f"{scanner}: invalid JSON at line {exc.lineno}"]


def parse_bandit(path: Path) -> ParsedReport:
    """Parse a Bandit ``-f json`` report."""
    report = ParsedReport(scanner="bandit")
    data, errors = _load_json(path, "bandit")
    if errors:
        report.errors = errors
        return report
    if not isinstance(data, dict) or not isinstance(data.get("results"), list):
        report.errors = ["bandit: unexpected report structure"]
        return report
    for result in data["results"]:
        if not isinstance(result, dict):
            continue
        report.findings.append(
            ScannerFinding(
                scanner="bandit",
                rule_id=str(result.get("test_id", "unknown")),
                severity=str(result.get("issue_severity", "UNKNOWN")).lower(),
                path=str(result.get("filename", "unknown")).replace("\\", "/"),
                line=int(result.get("line_number") or 0),
                message=str(result.get("issue_text", ""))[:500],
            )
        )
    return report


def parse_semgrep(path: Path) -> ParsedReport:
    """Parse a Semgrep report in native JSON or SARIF form."""
    report = ParsedReport(scanner="semgrep")
    data, errors = _load_json(path, "semgrep")
    if errors:
        report.errors = errors
        return report
    if isinstance(data, dict) and isinstance(data.get("results"), list):
        for result in data["results"]:
            if not isinstance(result, dict):
                continue
            extra = result.get("extra") or {}
            report.findings.append(
                ScannerFinding(
                    scanner="semgrep",
                    rule_id=str(result.get("check_id", "unknown")),
                    severity=str(extra.get("severity", "UNKNOWN")).lower(),
                    path=str(result.get("path", "unknown")).replace("\\", "/"),
                    line=int((result.get("start") or {}).get("line") or 0),
                    message=str(extra.get("message", ""))[:500],
                )
            )
        return report
    if isinstance(data, dict) and isinstance(data.get("runs"), list):
        for run in data["runs"]:
            for result in run.get("results") or []:
                if not isinstance(result, dict):
                    continue
                locations = result.get("locations") or [{}]
                physical = (locations[0].get("physicalLocation") or {}) if locations else {}
                artifact = (physical.get("artifactLocation") or {}).get("uri", "unknown")
                line = (physical.get("region") or {}).get("startLine") or 0
                report.findings.append(
                    ScannerFinding(
                        scanner="semgrep",
                        rule_id=str(result.get("ruleId", "unknown")),
                        severity=str(result.get("level", "UNKNOWN")).lower(),
                        path=str(artifact).replace("\\", "/"),
                        line=int(line),
                        message=str((result.get("message") or {}).get("text", ""))[:500],
                    )
                )
        return report
    report.errors = ["semgrep: unexpected report structure"]
    return report


def parse_pip_audit(path: Path) -> ParsedReport:
    """Parse a pip-audit ``--format json`` report (optional input)."""
    report = ParsedReport(scanner="pip-audit")
    data, errors = _load_json(path, "pip-audit")
    if errors:
        report.errors = errors
        return report
    dependencies = (
        data.get("dependencies") if isinstance(data, dict) else data
    )
    if not isinstance(dependencies, list):
        report.errors = ["pip-audit: unexpected report structure"]
        return report
    for dep in dependencies:
        if not isinstance(dep, dict):
            continue
        for vuln in dep.get("vulns") or []:
            report.findings.append(
                ScannerFinding(
                    scanner="pip-audit",
                    rule_id=str(vuln.get("id", "unknown")),
                    severity="unknown",
                    path=f"{dep.get('name', 'unknown')}=={dep.get('version', '?')}",
                    line=0,
                    message=str(vuln.get("description", ""))[:500],
                )
            )
    return report


def collect_findings(reports: list[ParsedReport]) -> list[ScannerFinding]:
    """Flatten reports, assign stable per-run finding ids, group duplicates.

    Grouping assigns a shared group_key to findings with the same scanner,
    rule and file. Every original finding remains in the returned list.
    """
    findings: list[ScannerFinding] = []
    for report in reports:
        findings.extend(report.findings)
    findings.sort(key=lambda f: (f.scanner, f.rule_id, f.path, f.line))
    for index, finding in enumerate(findings, start=1):
        finding.finding_id = f"{finding.scanner}-{index:03d}"
    return findings


def group_counts(findings: list[ScannerFinding]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding.group_key] = counts.get(finding.group_key, 0) + 1
    return counts
