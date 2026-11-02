"""Repeatable evaluation for semantic classification and evidence safeguards."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain import (
    AffectedField,
    ChangeStatus,
    CollectionType,
    SemanticClassification,
)
from app.services.ai_semantic_classification import (
    SemanticClassificationProvider,
    SemanticFieldDifference,
    SemanticProviderError,
)
from app.services.semantic_classification import (
    SemanticClassificationOutput,
    SemanticClassificationValidationError,
    SemanticEvidenceExcerpt,
    validate_semantic_citations,
)

ExpectedOutcome = Literal[
    "substantive",
    "wording_only",
    "needs_review",
    "not_applicable",
]
EvaluationCategory = Literal[
    "substantive",
    "paraphrase",
    "unchanged",
    "conflicting",
    "missing_evidence",
    "missing_field",
]


class SemanticEvaluationCase(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    case_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{2,79}$")
    category: EvaluationCategory
    description: str = Field(min_length=1, max_length=500)
    field: AffectedField
    deterministic_status: ChangeStatus
    from_value: str | None
    to_value: str | None
    evidence: list[SemanticEvidenceExcerpt]
    expected_outcome: ExpectedOutcome
    replay_output: SemanticClassificationOutput | None

    @model_validator(mode="after")
    def validate_case_shape(self) -> SemanticEvaluationCase:
        eligible = (
            self.deterministic_status == ChangeStatus.MODIFIED
            and self.from_value is not None
            and self.to_value is not None
        )
        if eligible and self.expected_outcome == "not_applicable":
            raise ValueError("An eligible modified field requires a semantic outcome.")
        if not eligible and self.expected_outcome != "not_applicable":
            raise ValueError("Unchanged or incomplete fields must be not_applicable.")
        if eligible and self.replay_output is None:
            raise ValueError("Eligible replay cases require a structured replay output.")
        if not eligible and self.replay_output is not None:
            raise ValueError("Ineligible cases must not include a replay output.")
        return self


class SemanticEvaluationSuite(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    fixture_version: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=500)
    cases: list[SemanticEvaluationCase] = Field(min_length=1)

    @model_validator(mode="after")
    def require_unique_case_ids(self) -> SemanticEvaluationSuite:
        case_ids = [case.case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("Evaluation case IDs must be unique.")
        return self


class SemanticEvaluationCaseResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    category: EvaluationCategory
    expected_outcome: ExpectedOutcome
    raw_outcome: ExpectedOutcome | None
    effective_outcome: ExpectedOutcome
    raw_correct: bool | None
    effective_correct: bool
    validation_error_code: str | None


class SemanticEvaluationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fixture_version: str
    fixture_sha256: str
    provider: str
    model: str
    total_cases: int
    eligible_cases: int
    skipped_cases: int
    raw_correct: int
    effective_correct: int
    raw_accuracy: float | None
    effective_accuracy: float | None
    skipped_correct: int
    evidence_validation_failures: int
    provider_failures: int
    needs_review_fallbacks: int
    results: list[SemanticEvaluationCaseResult]


def load_evaluation_suite(path: Path) -> tuple[SemanticEvaluationSuite, str]:
    content = path.read_bytes()
    suite = SemanticEvaluationSuite.model_validate_json(content)
    return suite, hashlib.sha256(content).hexdigest()


def _is_eligible(case: SemanticEvaluationCase) -> bool:
    return (
        case.deterministic_status == ChangeStatus.MODIFIED
        and case.from_value is not None
        and case.to_value is not None
    )


def _difference(case: SemanticEvaluationCase) -> SemanticFieldDifference:
    assert case.from_value is not None
    assert case.to_value is not None
    return SemanticFieldDifference(
        measure_id=f"EVAL-{case.case_id}",
        program="Fictional semantic evaluation fixture",
        collection_type=CollectionType.ECQM,
        from_year=2025,
        to_year=2026,
        field=case.field,
        deterministic_status=case.deterministic_status,
        from_value=case.from_value,
        to_value=case.to_value,
    )


def evaluate_semantic_suite(
    suite: SemanticEvaluationSuite,
    fixture_sha256: str,
    *,
    provider: SemanticClassificationProvider | None = None,
) -> SemanticEvaluationReport:
    """Evaluate fixture replay output or an explicitly supplied live provider."""

    provider_name = provider.provider_name if provider else "controlled-replay"
    model_name = provider.model_name if provider else suite.fixture_version
    results: list[SemanticEvaluationCaseResult] = []
    evidence_failures = 0
    provider_failures = 0
    fallbacks = 0

    for case in suite.cases:
        if not _is_eligible(case):
            effective: ExpectedOutcome = "not_applicable"
            results.append(
                SemanticEvaluationCaseResult(
                    case_id=case.case_id,
                    category=case.category,
                    expected_outcome=case.expected_outcome,
                    raw_outcome=None,
                    effective_outcome=effective,
                    raw_correct=None,
                    effective_correct=effective == case.expected_outcome,
                    validation_error_code=None,
                )
            )
            continue

        output: SemanticClassificationOutput | None = None
        error_code: str | None = None
        if provider is None:
            output = case.replay_output
        else:
            try:
                output = provider.classify(
                    difference=_difference(case),
                    evidence=case.evidence,
                ).output
            except SemanticProviderError as error:
                error_code = error.code
                provider_failures += 1

        raw_outcome: ExpectedOutcome | None = (
            output.classification.value if output is not None else None
        )
        if output is not None:
            try:
                validate_semantic_citations(output, case.evidence)
            except SemanticClassificationValidationError as error:
                error_code = error.code
                evidence_failures += 1

        if error_code is not None:
            effective_outcome: ExpectedOutcome = SemanticClassification.NEEDS_REVIEW.value
            fallbacks += 1
        elif raw_outcome is not None:
            effective_outcome = raw_outcome
        else:
            effective_outcome = SemanticClassification.NEEDS_REVIEW.value
            fallbacks += 1

        results.append(
            SemanticEvaluationCaseResult(
                case_id=case.case_id,
                category=case.category,
                expected_outcome=case.expected_outcome,
                raw_outcome=raw_outcome,
                effective_outcome=effective_outcome,
                raw_correct=raw_outcome == case.expected_outcome,
                effective_correct=effective_outcome == case.expected_outcome,
                validation_error_code=error_code,
            )
        )

    eligible_results = [result for result in results if result.raw_correct is not None]
    skipped_results = [result for result in results if result.raw_correct is None]
    raw_correct = sum(result.raw_correct is True for result in eligible_results)
    effective_correct = sum(result.effective_correct for result in eligible_results)
    return SemanticEvaluationReport(
        fixture_version=suite.fixture_version,
        fixture_sha256=fixture_sha256,
        provider=provider_name,
        model=model_name,
        total_cases=len(results),
        eligible_cases=len(eligible_results),
        skipped_cases=len(skipped_results),
        raw_correct=raw_correct,
        effective_correct=effective_correct,
        raw_accuracy=(raw_correct / len(eligible_results) if eligible_results else None),
        effective_accuracy=(
            effective_correct / len(eligible_results) if eligible_results else None
        ),
        skipped_correct=sum(result.effective_correct for result in skipped_results),
        evidence_validation_failures=evidence_failures,
        provider_failures=provider_failures,
        needs_review_fallbacks=fallbacks,
        results=results,
    )


def render_semantic_evaluation_report(report: SemanticEvaluationReport) -> str:
    replay = report.provider == "controlled-replay"
    heading = (
        "Controlled semantic-classification replay"
        if replay
        else "Live semantic-classification evaluation"
    )
    lines = [
        f"# {heading}",
        "",
        (
            "This is a deterministic safety-harness replay, not a live-model benchmark "
            "or a healthcare accuracy claim."
            if replay
            else (
                "This small fictional evaluation reflects the configured provider for this "
                "exact fixture revision; it is not a clinical or healthcare accuracy claim."
            )
        ),
        "",
        f"- Fixture version: `{report.fixture_version}`",
        f"- Fixture SHA-256: `{report.fixture_sha256}`",
        f"- Provider/model: `{report.provider}` / `{report.model}`",
        f"- Total cases: {report.total_cases}",
        f"- Provider-eligible cases: {report.eligible_cases}",
        f"- Correctly skipped deterministic cases: {report.skipped_correct}/{report.skipped_cases}",
        f"- Raw label accuracy: {_accuracy(report.raw_correct, report.eligible_cases)}",
        (
            "- Safety-adjusted accuracy after `needs_review` fallback: "
            f"{_accuracy(report.effective_correct, report.eligible_cases)}"
        ),
        f"- Evidence-validation failures: {report.evidence_validation_failures}",
        f"- Provider failures: {report.provider_failures}",
        f"- `needs_review` fallbacks: {report.needs_review_fallbacks}",
        "",
        "| Case | Category | Expected | Raw | Effective | Validation |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for result in report.results:
        lines.append(
            "| "
            + " | ".join(
                (
                    result.case_id,
                    result.category,
                    result.expected_outcome,
                    result.raw_outcome or "—",
                    result.effective_outcome,
                    result.validation_error_code or "—",
                )
            )
            + " |"
        )
    if replay:
        lines.extend(
            [
                "",
                "## Interpretation",
                "",
                "The replay outputs are intentionally mixed: they include correct labels, a "
                "valid misclassification, and a one-sided citation failure. The report proves "
                "that scoring and fail-closed evidence validation work; it does not measure an "
                "OpenAI model. Run the explicit live-provider command to produce model-specific "
                "results before making any model-performance statement.",
            ]
        )
    return "\n".join(lines) + "\n"


def _accuracy(correct: int, total: int) -> str:
    if total == 0:
        return "not measured"
    return f"{correct}/{total} ({correct / total:.1%})"


def report_as_json(report: SemanticEvaluationReport) -> str:
    return json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
