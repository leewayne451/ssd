"""Strict response schemas for AI workflow output.

Every model response is parsed as JSON and validated against one of these
Pydantic models with ``extra="forbid"``. Anything the model adds that is not
in the schema -- including instruction-like fields such as
``execute_command`` or ``run_shell`` -- is rejected as ordinary invalid data.
Nothing in a validated response is ever executed.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class SchemaValidationError(ValueError):
    """Raised when a model response does not match the required schema."""


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class OverallRisk(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Confidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FindingClassification(str, Enum):
    SECURITY = "security"
    IMPLEMENTATION_GAP = "implementation_gap"
    DOCUMENTATION_GAP = "documentation_gap"
    POSSIBLE_CONFLICT = "possible_conflict"
    TEST_GAP = "test_gap"


class TriageVerdict(str, Enum):
    LIKELY_TRUE_POSITIVE = "likely_true_positive"
    LIKELY_FALSE_POSITIVE = "likely_false_positive"
    NEEDS_INVESTIGATION = "needs_investigation"


class AuditClassification(str, Enum):
    CONSISTENT = "CONSISTENT"
    IMPLEMENTATION_GAP = "IMPLEMENTATION_GAP"
    DOCUMENTATION_GAP = "DOCUMENTATION_GAP"
    POSSIBLE_CONFLICT = "POSSIBLE_CONFLICT"
    TEST_GAP = "TEST_GAP"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


STRIDE_CATEGORIES = (
    "Spoofing",
    "Tampering",
    "Repudiation",
    "Information Disclosure",
    "Denial of Service",
    "Elevation of Privilege",
)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_max_length=20_000)


# ---------------------------------------------------------------------------
# Phase 5 -- contextual PR review
# ---------------------------------------------------------------------------


class PRReviewFinding(_StrictModel):
    id: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=300)
    severity: Severity
    confidence: Confidence
    classification: FindingClassification
    files: list[str] = Field(max_length=30)
    evidence: str
    impact: str
    recommendation: str
    project_requirements: list[str] = Field(max_length=30)
    misuse_cases: list[str] = Field(max_length=30)
    stride: list[str] = Field(max_length=6)
    owasp_mapping: list[str] = Field(max_length=15)
    suggested_tests: list[str] = Field(max_length=15)


class PRReviewResponse(_StrictModel):
    overall_risk: OverallRisk
    summary: str
    findings: list[PRReviewFinding] = Field(max_length=50)
    positive_controls: list[str] = Field(max_length=30)
    insufficient_evidence: list[str] = Field(max_length=30)
    truncated: bool


# ---------------------------------------------------------------------------
# Phase 7 -- scanner triage
# ---------------------------------------------------------------------------


class TriageAssessment(_StrictModel):
    finding_id: str = Field(min_length=1, max_length=120)
    verdict: TriageVerdict
    confidence: Confidence
    application_impact: str
    recommended_investigation: str
    recommended_remediation: str
    suggested_regression_test: str
    project_requirements: list[str] = Field(max_length=20)
    owasp_mapping: list[str] = Field(max_length=10)
    nist_relevance: list[str] = Field(max_length=10)
    osa_classification: list[str] = Field(max_length=10)


class TriageResponse(_StrictModel):
    summary: str
    assessments: list[TriageAssessment] = Field(max_length=300)
    insufficient_evidence: list[str] = Field(max_length=30)
    truncated: bool


# ---------------------------------------------------------------------------
# Phase 8 -- milestone consistency audit
# ---------------------------------------------------------------------------


class AuditItem(_StrictModel):
    id: str = Field(min_length=1, max_length=80)
    section: str = Field(min_length=1, max_length=120)
    classification: AuditClassification
    severity: Severity
    title: str = Field(min_length=1, max_length=300)
    detail: str
    evidence: str
    recommendation: str
    project_requirements: list[str] = Field(max_length=30)


class MilestoneAuditResponse(_StrictModel):
    executive_summary: str
    items: list[AuditItem] = Field(max_length=200)
    prioritised_actions: list[str] = Field(max_length=40)
    insufficient_evidence: list[str] = Field(max_length=40)
    truncated: bool


# ---------------------------------------------------------------------------
# Validation and strict JSON Schema helpers
# ---------------------------------------------------------------------------


def validate_response(model_cls: type[BaseModel], data: Any) -> BaseModel:
    """Validate untrusted decoded JSON against a schema.

    Raises SchemaValidationError on any mismatch, including unknown fields.
    """
    if not isinstance(data, dict):
        raise SchemaValidationError(
            f"expected a JSON object for {model_cls.__name__}, "
            f"got {type(data).__name__}"
        )
    try:
        return model_cls.model_validate(data)
    except ValidationError as exc:
        raise SchemaValidationError(
            f"response failed {model_cls.__name__} validation: {exc}"
        ) from exc


def _make_strict(node: Any) -> None:
    """Recursively adjust a JSON Schema for OpenAI strict structured output.

    Strict mode requires every object to set additionalProperties=false and
    to list all properties as required.
    """
    if isinstance(node, dict):
        if node.get("type") == "object" and "properties" in node:
            node["additionalProperties"] = False
            node["required"] = list(node["properties"].keys())
        for value in node.values():
            _make_strict(value)
    elif isinstance(node, list):
        for value in node:
            _make_strict(value)


def strict_json_schema(model_cls: type[BaseModel]) -> dict[str, Any]:
    """Produce a strict-mode JSON Schema for the given response model."""
    schema = model_cls.model_json_schema()
    _make_strict(schema)
    return schema
