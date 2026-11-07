from pathlib import Path

from app.services.impact_evaluation import (
    evaluate_impact_suite,
    load_impact_evaluation_suite,
    render_impact_evaluation_report,
)

FIXTURES = Path(__file__).parents[1] / "app" / "data" / "impact_explanation_eval_v1.json"


def test_controlled_impact_replay_records_expected_safety_outcomes() -> None:
    suite, digest = load_impact_evaluation_suite(FIXTURES)
    report = evaluate_impact_suite(suite, digest)

    assert report.total_cases == 7
    assert report.passed_cases == 7
    assert report.schema_rejections == 1
    assert report.evidence_rejections == 2
    assert len(report.fixture_sha256) == 64
    assert {result.category for result in report.results} == {
        "calculation_change",
        "membership_change",
        "wording_only",
        "insufficient_evidence",
        "unsupported_citation",
        "role_relevance",
    }
    markdown = render_impact_evaluation_report(report)
    assert "not a live-model benchmark" in markdown
    assert "7/7" in markdown
