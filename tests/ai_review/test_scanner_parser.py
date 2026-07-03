"""Scanner report parsing: every original finding preserved, duplicates grouped."""

import json
from pathlib import Path

import pytest

from tools.ai_review.scanner_parser import (
    collect_findings,
    group_counts,
    parse_bandit,
    parse_pip_audit,
    parse_semgrep,
)

FIXTURES = Path(__file__).parent / "fixtures"


class TestBandit:
    def test_bandit_json_parsed(self):
        report = parse_bandit(FIXTURES / "bandit-sample.json")
        assert report.ok
        assert len(report.findings) == 3
        first = report.findings[0]
        assert first.scanner == "bandit"
        assert first.rule_id == "B602"
        assert first.severity == "high"
        assert first.path == "app/services/backup_service.py"
        assert first.line == 42
        assert "shell=True" in first.message


class TestSemgrep:
    def test_semgrep_json_parsed(self):
        report = parse_semgrep(FIXTURES / "semgrep-sample.json")
        assert report.ok
        assert len(report.findings) == 1
        finding = report.findings[0]
        assert finding.rule_id.endswith("render-template-string")
        assert finding.path == "app/web/routes/listing_routes.py"
        assert finding.line == 88

    def test_semgrep_sarif_parsed(self):
        report = parse_semgrep(FIXTURES / "semgrep-sample.sarif")
        assert report.ok
        assert len(report.findings) == 1
        assert report.findings[0].path == "app/services/backup_service.py"
        assert report.findings[0].severity == "error"


class TestRobustness:
    def test_empty_report(self, tmp_path):
        path = tmp_path / "empty.json"
        path.write_text(json.dumps({"results": []}))
        assert parse_bandit(path).findings == []
        assert parse_semgrep(path).findings == []

    def test_missing_report(self, tmp_path):
        report = parse_bandit(tmp_path / "nope.json")
        assert not report.ok
        assert report.findings == []

    def test_invalid_json(self, tmp_path):
        path = tmp_path / "broken.json"
        path.write_text("{not json")
        for parser in (parse_bandit, parse_semgrep, parse_pip_audit):
            report = parser(path)
            assert not report.ok
            assert report.findings == []

    def test_unexpected_structure(self, tmp_path):
        path = tmp_path / "odd.json"
        path.write_text(json.dumps({"unexpected": True}))
        assert not parse_bandit(path).ok
        assert not parse_semgrep(path).ok


class TestCollection:
    def test_duplicate_grouping_preserves_originals(self):
        bandit = parse_bandit(FIXTURES / "bandit-sample.json")
        semgrep = parse_semgrep(FIXTURES / "semgrep-sample.json")
        findings = collect_findings([bandit, semgrep])
        # Nothing deleted: 3 bandit + 1 semgrep.
        assert len(findings) == 4
        counts = group_counts(findings)
        # The two B201 hits in manage.py share one group.
        assert counts["bandit:B201:manage.py"] == 2

    def test_stable_finding_ids_assigned(self):
        findings = collect_findings([parse_bandit(FIXTURES / "bandit-sample.json")])
        assert [f.finding_id for f in findings] == [
            "bandit-001",
            "bandit-002",
            "bandit-003",
        ]


class TestPipAudit:
    def test_pip_audit_json_parsed(self, tmp_path):
        path = tmp_path / "pip-audit.json"
        path.write_text(
            json.dumps(
                {
                    "dependencies": [
                        {
                            "name": "flask",
                            "version": "0.1",
                            "vulns": [
                                {"id": "GHSA-xxxx", "description": "old flask bug"}
                            ],
                        },
                        {"name": "jinja2", "version": "3.1.4", "vulns": []},
                    ]
                }
            )
        )
        report = parse_pip_audit(path)
        assert report.ok
        assert len(report.findings) == 1
        assert report.findings[0].rule_id == "GHSA-xxxx"
        assert report.findings[0].path == "flask==0.1"
