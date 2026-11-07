"""Repeatable evaluation of the impact schema and evidence safeguards."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.services.impact_explanation import (
    ImpactExplanationOutput,
    ImpactExplanationValidationError,
    validate_impact_citations,
)
from app.services.semantic_classification import SemanticEvidenceExcerpt

EvaluationCategory = Literal[
    "calculation_change",
    "membership_change",
    "wording_only",
    "insufficient_evidence",
    "unsupported_citation",
    "role_relevance",
]
ExpectedResult = Literal["accepted", "rejected"]


class ImpactEvaluationCase(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    case_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{2,79}$")
    category: EvaluationCategory
    description: str = Field(min_length=1, max_length=500)
    evidence: list[SemanticEvidenceExcerpt] = Field(min_length=1)
    replay_output: dict[str, object]
    expected_result: ExpectedResult
    expected_error_code: str | None = None

    @model_validator(mode="after")
    def validate_expectation(self) -> ImpactEvaluationCase:
        if self.expected_result == "accepted" and self.expected_error_code is not None:
            raise ValueError("Accepted cases cannot expect an error code.")
        if self.expected_result == "rejected" and self.expected_error_code is None:
            raise ValueError("Rejected cases require an expected error code.")
        return self


class ImpactEvaluationSuite(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    fixture_version: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=500)
    cases: list[ImpactEvaluationCase] = Field(min_length=1)

    @model_validator(mode="after")
    def require_unique_case_ids(self) -> ImpactEvaluationSuite:
        ids = [case.case_id for case in self.cases]
        if len(ids) != len(set(ids)):
            raise ValueError("Evaluation case IDs must be unique.")
        return self


class ImpactEvaluationCaseResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    category: EvaluationCategory
    expected_result: ExpectedResult
    actual_result: ExpectedResult
    expected_error_code: str | None
    actual_error_code: str | None
    passed: bool


class ImpactEvaluationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fixture_version: str
    fixture_sha256: str
    provider: Literal["controlled-replay"]
    total_cases: int
    passed_cases: int
    schema_rejections: int
    evidence_rejections: int
    results: list[ImpactEvaluationCaseResult]


def load_impact_evaluation_suite(
    path: Path,
) -> tuple[ImpactEvaluationSuite, str]:
    content = path.read_bytes()
    return (
        ImpactEvaluationSuite.model_validate_json(content),
        hashlib.sha256(content).hexdigest(),
    )


def evaluate_impact_suite(
    suite: ImpactEvaluationSuite,
    fixture_sha256: str,
) -> ImpactEvaluationReport:
    results: list[ImpactEvaluationCaseResult] = []
    schema_rejections = 0
    evidence_rejections = 0
    for case in suite.cases:
        error_code: str | None = None
        try:
            output = ImpactExplanationOutput.model_validate(case.replay_output)
            validate_impact_citations(output, case.evidence)
        except ValidationError:
            error_code = "impact_schema_invalid"
            schema_rejections += 1
        except ImpactExplanationValidationError as error:
            error_code = error.code
            evidence_rejections += 1
        actual: ExpectedResult = "rejected" if error_code else "accepted"
        results.append(
            ImpactEvaluationCaseResult(
                case_id=case.case_id,
                category=case.category,
                expected_result=case.expected_result,
                actual_result=actual,
                expected_error_code=case.expected_error_code,
                actual_error_code=error_code,
                passed=(actual == case.expected_result and error_code == case.expected_error_code),
            )
        )
    return ImpactEvaluationReport(
        fixture_version=suite.fixture_version,
        fixture_sha256=fixture_sha256,
        provider="controlled-replay",
        total_cases=len(results),
        passed_cases=sum(result.passed for result in results),
        schema_rejections=schema_rejections,
        evidence_rejections=evidence_rejections,
        results=results,
    )


def render_impact_evaluation_report(report: ImpactEvaluationReport) -> str:
    lines = [
        "# Controlled impact-explanation replay",
        "",
        "This deterministic safety replay uses explicitly fictional content. It tests the "
        "schema and citation boundary; it is not a live-model benchmark, clinical claim, "
        "or proof that an implication is operationally useful.",
        "",
        f"- Fixture version: `{report.fixture_version}`",
        f"- Fixture SHA-256: `{report.fixture_sha256}`",
        f"- Cases passing expected safeguards: {report.passed_cases}/{report.total_cases}",
        f"- Schema rejections: {report.schema_rejections}",
        f"- Evidence rejections: {report.evidence_rejections}",
        "",
        "| Case | Category | Expected | Actual | Expected error | Actual error | Pass |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for result in report.results:
        lines.append(
            "| "
            + " | ".join(
                (
                    result.case_id,
                    result.category,
                    result.expected_result,
                    result.actual_result,
                    result.expected_error_code or "—",
                    result.actual_error_code or "—",
                    "yes" if result.passed else "no",
                )
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The accepted calculation, membership, and wording fixtures demonstrate valid "
            "paired role output. The rejected fixtures demonstrate fail-closed handling for "
            "one-sided summaries, unknown evidence IDs, and role statements mislabeled as "
            "source facts. Human review remains necessary for factual accuracy, role relevance, "
            "and usefulness before any later publication step.",
        ]
    )
    return "\n".join(lines) + "\n"


def report_as_json(report: ImpactEvaluationReport) -> str:
    return json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
