from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import ImpactExplanationReviewDecision, PublicationState
from app.models import ImpactExplanationDraft, MeasureComparison
from app.services.ai_impact_explanation import (
    ImpactComparisonInput,
    ImpactExplanationProvider,
    ImpactProviderResult,
    generate_impact_explanation,
)
from app.services.impact_explanation import (
    ACOQualityManagerImpact,
    DataAnalystImpact,
    ImpactCitation,
    ImpactExplanationOutput,
    ImpactStatement,
    ImpactStatementType,
    ImpactUncertaintyCaveat,
)
from app.services.semantic_classification import SemanticEvidenceExcerpt

DETAIL_PARAMETERS = {
    "program": "Fictional Quality Program",
    "collection_type": "program_roster",
    "from_year": 2025,
    "to_year": 2026,
}


class StoredImpactProvider(ImpactExplanationProvider):
    provider_name = "test-provider"
    model_name = "test-impact-model"

    def generate(
        self,
        *,
        comparison: ImpactComparisonInput,
        evidence: list[SemanticEvidenceExcerpt],
    ) -> ImpactProviderResult:
        citations = [ImpactCitation(evidence_id=item.evidence_id) for item in evidence]
        from_citation = [citations[0]]
        possible_analyst = ImpactStatement(
            statement="Analysts may need to rerun year-specific validation cases.",
            statement_type=ImpactStatementType.POSSIBLE_IMPACT,
            citations=from_citation,
        )
        possible_manager = ImpactStatement(
            statement="Quality teams may need to coordinate a reporting review.",
            statement_type=ImpactStatementType.POSSIBLE_IMPACT,
            citations=from_citation,
        )
        return ImpactProviderResult(
            output=ImpactExplanationOutput(
                plain_language_summary=ImpactStatement(
                    statement="The approved fictional definition differs between years.",
                    statement_type=ImpactStatementType.SOURCE_FACT,
                    citations=citations,
                ),
                data_analyst=DataAnalystImpact(
                    technical_implications=[possible_analyst],
                    validation_considerations=[possible_analyst],
                ),
                aco_quality_manager=ACOQualityManagerImpact(
                    operational_implications=[possible_manager],
                    coordination_considerations=[possible_manager],
                ),
                uncertainty_caveats=[
                    ImpactUncertaintyCaveat(
                        statement="This is a possible impact, not CMS policy.",
                        citations=from_citation,
                    )
                ],
            ),
            response_id="stored-impact-response",
        )


def _comparison(session: Session) -> MeasureComparison:
    comparison = session.scalar(select(MeasureComparison))
    assert comparison is not None
    return comparison


def _generated_draft(session: Session) -> ImpactExplanationDraft:
    return generate_impact_explanation(
        session,
        _comparison(session),
        provider=StoredImpactProvider(),
        created_by="generator",
    )


def _publish(draft: ImpactExplanationDraft) -> None:
    reviewed_at = datetime(2026, 11, 6, 12, tzinfo=UTC)
    draft.review_decision = ImpactExplanationReviewDecision.APPROVE
    draft.approved_output_payload = draft.output_payload
    draft.reviewed_at = reviewed_at
    draft.reviewed_by = "human-reviewer"
    draft.publication_state = PublicationState.PUBLISHED
    draft.published_at = reviewed_at
    draft.published_by = "human-reviewer"


def test_public_endpoint_returns_only_the_stored_human_approved_pair(
    client: TestClient,
    seeded_session: Session,
) -> None:
    draft = _generated_draft(seeded_session)
    _publish(draft)
    seeded_session.commit()

    response = client.get(
        "/api/changes/DEMO-001/impact-explanation",
        params=DETAIL_PARAMETERS,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["measure_id"] == "DEMO-001"
    assert payload["approved_at"] == "2026-11-06T12:00:00Z"
    assert payload["output"]["data_analyst"]["technical_implications"][0][
        "statement"
    ].startswith("Analysts may")
    assert payload["output"]["aco_quality_manager"]["operational_implications"][0][
        "statement"
    ].startswith("Quality teams may")
    assert {item["side"] for item in payload["evidence"]} == {
        "from_version",
        "to_version",
    }
    assert "provider" not in payload
    assert "input_digest" not in payload
    assert "created_by" not in payload


@pytest.mark.parametrize("state", ["pending", "rejected", "outdated", "stale_input"])
def test_nonpublic_or_outdated_explanations_are_withheld(
    client: TestClient,
    seeded_session: Session,
    state: str,
) -> None:
    draft = _generated_draft(seeded_session)
    now = datetime(2026, 11, 6, 12, tzinfo=UTC)
    if state == "rejected":
        draft.review_decision = ImpactExplanationReviewDecision.REJECT
        draft.reviewed_at = now
        draft.reviewed_by = "human-reviewer"
    elif state in {"outdated", "stale_input"}:
        _publish(draft)
        if state == "outdated":
            draft.outdated_at = now
        else:
            draft.input_digest = "0" * 64
    seeded_session.commit()

    response = client.get(
        "/api/changes/DEMO-001/impact-explanation",
        params=DETAIL_PARAMETERS,
    )

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_public_impact_endpoint_validates_the_complete_comparison_identity(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/changes/DEMO-001/impact-explanation",
        params={**DETAIL_PARAMETERS, "program": "Another Program"},
    )

    assert response.status_code == 404
