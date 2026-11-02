import sys
from pathlib import Path

import pytest

from app.commands import evaluate_semantic_classification as evaluation_command
from app.services.ai_semantic_classification import (
    SemanticClassificationProvider,
    SemanticFieldDifference,
    SemanticProviderError,
    SemanticProviderResult,
)
from app.services.semantic_classification import SemanticEvidenceExcerpt
from app.services.semantic_evaluation import (
    SemanticEvaluationSuite,
    evaluate_semantic_suite,
    load_evaluation_suite,
    render_semantic_evaluation_report,
    report_as_json,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "app" / "data" / "semantic_classification_eval_v1.json"
)
CHECKED_REPORT_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "evaluations"
    / "semantic-classification-replay.md"
)


def _controlled_report():
    suite, fixture_sha256 = load_evaluation_suite(FIXTURE_PATH)
    return suite, evaluate_semantic_suite(suite, fixture_sha256)


class OneFailureProvider(SemanticClassificationProvider):
    provider_name = "test-provider"
    model_name = "test-model"

    def __init__(self, suite: SemanticEvaluationSuite) -> None:
        self.outputs = {
            case.case_id: case.replay_output
            for case in suite.cases
            if case.replay_output is not None
        }

    def classify(
        self,
        *,
        difference: SemanticFieldDifference,
        evidence: list[SemanticEvidenceExcerpt],
    ) -> SemanticProviderResult:
        del evidence
        case_id = difference.measure_id.removeprefix("EVAL-")
        if case_id == "conflicting_source_context":
            raise SemanticProviderError(
                "semantic_provider_error",
                "Synthetic transport failure.",
            )
        return SemanticProviderResult(
            output=self.outputs[case_id],
            response_id=f"test-response-{case_id}",
        )


def test_fixture_covers_required_semantic_and_evidence_cases() -> None:
    suite, _ = load_evaluation_suite(FIXTURE_PATH)

    assert {case.category for case in suite.cases} == {
        "substantive",
        "paraphrase",
        "unchanged",
        "conflicting",
        "missing_evidence",
        "missing_field",
    }
    assert "fictional" in suite.description.lower()
    assert all(
        "controlled fictional" in item.document_title.lower()
        for case in suite.cases
        for item in case.evidence
    )


def test_controlled_replay_reports_exact_safety_harness_results() -> None:
    _, report = _controlled_report()

    assert report.provider == "controlled-replay"
    assert report.total_cases == 7
    assert report.eligible_cases == 5
    assert report.skipped_cases == 2
    assert report.skipped_correct == 2
    assert report.raw_correct == 3
    assert report.raw_accuracy == pytest.approx(0.6)
    assert report.effective_correct == 4
    assert report.effective_accuracy == pytest.approx(0.8)
    assert report.evidence_validation_failures == 1
    assert report.provider_failures == 0
    assert report.needs_review_fallbacks == 1


def test_evidence_failure_falls_closed_but_valid_wrong_label_remains_visible() -> None:
    _, report = _controlled_report()
    results = {result.case_id: result for result in report.results}

    missing_evidence = results["missing_comparison_year_evidence"]
    assert missing_evidence.raw_outcome == "substantive"
    assert missing_evidence.effective_outcome == "needs_review"
    assert missing_evidence.validation_error_code == ("semantic_citation_coverage_incomplete")

    misclassified = results["substantive_eligibility_misclassified"]
    assert misclassified.validation_error_code is None
    assert misclassified.raw_outcome == "wording_only"
    assert misclassified.effective_outcome == "wording_only"
    assert misclassified.effective_correct is False


def test_provider_failure_is_counted_and_falls_closed() -> None:
    suite, fixture_sha256 = load_evaluation_suite(FIXTURE_PATH)

    report = evaluate_semantic_suite(
        suite,
        fixture_sha256,
        provider=OneFailureProvider(suite),
    )
    results = {result.case_id: result for result in report.results}

    assert report.provider == "test-provider"
    assert report.model == "test-model"
    assert report.provider_failures == 1
    failed = results["conflicting_source_context"]
    assert failed.raw_outcome is None
    assert failed.effective_outcome == "needs_review"
    assert failed.validation_error_code == "semantic_provider_error"


def test_report_distinguishes_replay_from_live_model_benchmark() -> None:
    _, report = _controlled_report()

    markdown = render_semantic_evaluation_report(report)
    assert "not a live-model benchmark or a healthcare accuracy claim" in markdown
    assert "Raw label accuracy: 3/5 (60.0%)" in markdown
    assert "Safety-adjusted accuracy after `needs_review` fallback: 4/5 (80.0%)" in markdown
    assert "it does not measure an OpenAI model" in markdown

    json_report = report_as_json(report)
    assert '"provider": "controlled-replay"' in json_report
    assert '"evidence_validation_failures": 1' in json_report


def test_checked_report_matches_the_versioned_replay() -> None:
    _, report = _controlled_report()

    assert CHECKED_REPORT_PATH.read_text(encoding="utf-8") == (
        render_semantic_evaluation_report(report)
    )


def test_suite_rejects_duplicate_case_ids() -> None:
    suite, _ = load_evaluation_suite(FIXTURE_PATH)
    duplicated = suite.model_dump(mode="json")
    duplicated["cases"].append(duplicated["cases"][0])

    with pytest.raises(ValueError, match="Evaluation case IDs must be unique"):
        SemanticEvaluationSuite.model_validate(duplicated)


def test_cli_requires_explicit_confirmation_for_live_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["evaluate_semantic_classification", "--provider", "openai"],
    )

    with pytest.raises(SystemExit) as error:
        evaluation_command.main()

    assert error.value.code == 2
