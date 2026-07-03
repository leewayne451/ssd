"""Deterministic Markdown rendering of validated responses."""

from tools.ai_review.render import (
    PR_REVIEW_MARKER,
    TRIAGE_MARKER,
    RenderMeta,
    escape_text,
    render_pr_review,
    render_triage,
)
from tools.ai_review.scanner_parser import ScannerFinding
from tools.ai_review.schemas import (
    PRReviewResponse,
    TriageResponse,
    validate_response,
)

from .test_schemas import valid_review_response

META = RenderMeta(model="gpt-5.4-mini", input_tokens=1000, output_tokens=200)


def _response(**overrides) -> PRReviewResponse:
    data = valid_review_response()
    data.update(overrides)
    return validate_response(PRReviewResponse, data)


class TestPRReviewRendering:
    def test_stable_marker_present(self, settings):
        body = render_pr_review(_response(), META, settings)
        assert body.startswith(PR_REVIEW_MARKER)

    def test_severity_sorting(self, settings):
        data = valid_review_response()
        low = dict(data["findings"][0], id="F-LOW", severity="low", title="Low one")
        critical = dict(
            data["findings"][0], id="F-CRIT", severity="critical", title="Crit one"
        )
        data["findings"] = [low, critical]
        body = render_pr_review(
            validate_response(PRReviewResponse, data), META, settings
        )
        assert body.index("F-CRIT") < body.index("F-LOW")

    def test_untrusted_content_escaped(self, settings):
        data = valid_review_response()
        data["summary"] = "<script>alert(1)</script> | ```injection```"
        body = render_pr_review(
            validate_response(PRReviewResponse, data), META, settings
        )
        assert "<script>" not in body
        assert "&lt;script&gt;" in body

    def test_secret_like_output_redacted(self, settings):
        data = valid_review_response()
        data["summary"] = "leaked key sk-proj-abcdefghijklmnop12345678"
        body = render_pr_review(
            validate_response(PRReviewResponse, data), META, settings
        )
        assert "sk-proj-abcdefghijklmnop12345678" not in body

    def test_empty_findings_rendering(self, settings):
        body = render_pr_review(
            _response(findings=[], overall_risk="none"), META, settings
        )
        assert "No supported findings" in body

    def test_truncation_notice(self, settings):
        body = render_pr_review(_response(truncated=True), META, settings)
        assert "truncated" in body.lower()
        assert "not** assessed" in body.lower() or "NOT" in body

    def test_token_usage_footer(self, settings):
        body = render_pr_review(_response(), META, settings)
        assert "gpt-5.4-mini" in body
        assert "input 1000" in body
        assert "output 200" in body

    def test_comment_length_cap(self, settings):
        data = valid_review_response()
        data["summary"] = "long words " * 1500
        body = render_pr_review(
            validate_response(PRReviewResponse, data), META, settings
        )
        assert len(body) <= settings.max_comment_chars


class TestTriageRendering:
    def test_no_findings_no_model(self, settings):
        body = render_triage(
            [], None, RenderMeta(model="none (no findings)"), settings
        )
        assert body.startswith(TRIAGE_MARKER)
        assert "No scanner findings" in body
        assert "No AI call" in body

    def test_findings_rendered_with_original_data(self, settings):
        finding = ScannerFinding(
            scanner="bandit",
            rule_id="B602",
            severity="high",
            path="app/services/backup_service.py",
            line=42,
            message="subprocess call with shell=True identified",
            finding_id="bandit-001",
        )
        response = validate_response(
            TriageResponse,
            {
                "summary": "One high finding.",
                "assessments": [
                    {
                        "finding_id": "bandit-001",
                        "verdict": "likely_true_positive",
                        "confidence": "high",
                        "application_impact": "command injection in backups",
                        "recommended_investigation": "check call sites",
                        "recommended_remediation": "avoid shell=True",
                        "suggested_regression_test": "test backup path quoting",
                        "project_requirements": [],
                        "owasp_mapping": ["A03:2021 Injection"],
                        "nist_relevance": ["SSDF PW.4"],
                        "osa_classification": ["SDR"],
                    }
                ],
                "insufficient_evidence": [],
                "truncated": False,
            },
        )
        body = render_triage([finding], response, META, settings)
        assert "B602" in body
        assert "app/services/backup_service.py" in body
        assert "likely true positive" in body
        assert "not suppressed" not in body.split("likely true positive")[0]

    def test_false_positive_stays_visible(self, settings):
        finding = ScannerFinding(
            scanner="bandit",
            rule_id="B101",
            severity="low",
            path="tests/conftest.py",
            line=5,
            message="assert used",
            finding_id="bandit-001",
        )
        response = validate_response(
            TriageResponse,
            {
                "summary": "Probably fine.",
                "assessments": [
                    {
                        "finding_id": "bandit-001",
                        "verdict": "likely_false_positive",
                        "confidence": "high",
                        "application_impact": "none",
                        "recommended_investigation": "confirm test-only",
                        "recommended_remediation": "none needed",
                        "suggested_regression_test": "n/a",
                        "project_requirements": [],
                        "owasp_mapping": [],
                        "nist_relevance": [],
                        "osa_classification": [],
                    }
                ],
                "insufficient_evidence": [],
                "truncated": False,
            },
        )
        body = render_triage([finding], response, META, settings)
        # The original finding is still fully rendered, not suppressed.
        assert "B101" in body
        assert "tests/conftest.py" in body
        assert "not suppressed" in body


class TestEscape:
    def test_escape_neutralises_markup(self):
        assert escape_text("<b>|```") == "&lt;b&gt;&#124;`​``"
