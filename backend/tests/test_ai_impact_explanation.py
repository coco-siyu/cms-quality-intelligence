import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import hash_admin_password
from app.config import Settings, get_settings
from app.domain import ComparisonEvidenceStatus, ComparisonReviewDecision
from app.models import ImpactExplanationDraft, MeasureComparison
from app.repositories.admin_impact_explanations import list_impact_explanation_drafts
from app.services.ai_impact_explanation import (
    ImpactComparisonInput,
    ImpactExplanationProvider,
    ImpactGenerationError,
    ImpactProviderError,
    ImpactProviderResult,
    generate_impact_explanation,
    provider_from_settings,
)
from app.services.impact_explanation import (
    ACOQualityManagerImpact,
    DataAnalystImpact,
    ImpactCitation,
    ImpactExplanationOutput,
    ImpactStatement,
    ImpactStatementType,
)
from app.services.semantic_classification import SemanticEvidenceExcerpt


class FakeImpactProvider(ImpactExplanationProvider):
    provider_name = "test-provider"
    model_name = "test-impact-model"

    def __init__(self, mode: str = "valid") -> None:
        self.mode = mode
        self.calls = 0

    def generate(
        self,
        *,
        comparison: ImpactComparisonInput,
        evidence: list[SemanticEvidenceExcerpt],
    ) -> ImpactProviderResult:
        self.calls += 1
        assert comparison.measure_id == "DEMO-001"
        assert comparison.from_year == 2025
        assert comparison.to_year == 2026
        if self.mode == "transport_error":
            raise ImpactProviderError("impact_provider_error", "Synthetic failure.")
        evidence_ids = [item.evidence_id for item in evidence]
        summary_ids = evidence_ids
        if self.mode == "one_sided":
            summary_ids = evidence_ids[:1]
        elif self.mode == "unsupported":
            summary_ids = [evidence_ids[0], "NOT-SUPPLIED"]
        implication = ImpactStatement(
            statement="A team may need to inspect this fictional change.",
            statement_type=ImpactStatementType.POSSIBLE_IMPACT,
            citations=[ImpactCitation(evidence_id=evidence_ids[0])],
        )
        return ImpactProviderResult(
            output=ImpactExplanationOutput(
                plain_language_summary=ImpactStatement(
                    statement="The two fictional year values differ.",
                    statement_type=ImpactStatementType.SOURCE_FACT,
                    citations=[ImpactCitation(evidence_id=item) for item in summary_ids],
                ),
                data_analyst=DataAnalystImpact(
                    technical_implications=[implication],
                    validation_considerations=[implication],
                ),
                aco_quality_manager=ACOQualityManagerImpact(
                    operational_implications=[implication],
                    coordination_considerations=[implication],
                ),
                uncertainty_caveats=[],
            ),
            response_id="response-impact-test-001",
        )


def _comparison(session: Session) -> MeasureComparison:
    comparison = session.scalar(select(MeasureComparison))
    assert comparison is not None
    assert comparison.evidence_status == ComparisonEvidenceStatus.VERIFIED
    return comparison


def test_generation_persists_an_idempotent_private_cited_draft(
    seeded_session: Session,
) -> None:
    comparison = _comparison(seeded_session)
    provider = FakeImpactProvider()

    first = generate_impact_explanation(
        seeded_session, comparison, provider=provider, created_by="admin"
    )
    repeated = generate_impact_explanation(
        seeded_session, comparison, provider=provider, created_by="admin"
    )
    seeded_session.commit()

    assert repeated.id == first.id
    assert provider.calls == 1
    assert first.prompt_version == "cms-impact-explanation-v1"
    assert first.provider_response_id == "response-impact-test-001"
    assert first.output_payload["plain_language_summary"]["statement_type"] == "source_fact"
    assert len(first.input_digest) == 64
    assert {
        item.comparison_evidence.evidence_reference.evidence_id for item in first.citations
    } == {"DEMO-EVIDENCE-DEMO-001-2025", "DEMO-EVIDENCE-DEMO-001-2026"}
    assert seeded_session.query(ImpactExplanationDraft).count() == 1
    assert comparison.review_decision == ComparisonReviewDecision.APPROVE
    private_page = list_impact_explanation_drafts(seeded_session, comparison_id=comparison.id)
    assert private_page.items[0].draft_id == first.draft_id
    assert private_page.items[0].cited_evidence_ids == [
        "DEMO-EVIDENCE-DEMO-001-2025",
        "DEMO-EVIDENCE-DEMO-001-2026",
    ]


@pytest.mark.parametrize(
    ("mode", "code"),
    [
        ("one_sided", "impact_summary_citation_coverage_incomplete"),
        ("unsupported", "impact_citation_unsupported"),
    ],
)
def test_invalid_citations_fail_closed_without_persisting(
    seeded_session: Session, mode: str, code: str
) -> None:
    with pytest.raises(ImpactGenerationError) as error:
        generate_impact_explanation(
            seeded_session,
            _comparison(seeded_session),
            provider=FakeImpactProvider(mode),
            created_by="admin",
        )

    assert error.value.code == code
    assert seeded_session.query(ImpactExplanationDraft).count() == 0


def test_transport_failure_is_retryable_and_not_persisted(
    seeded_session: Session,
) -> None:
    with pytest.raises(ImpactProviderError) as error:
        generate_impact_explanation(
            seeded_session,
            _comparison(seeded_session),
            provider=FakeImpactProvider("transport_error"),
            created_by="admin",
        )
    assert error.value.code == "impact_provider_error"
    assert seeded_session.query(ImpactExplanationDraft).count() == 0


def test_generation_requires_approval_and_fresh_verified_evidence(
    seeded_session: Session,
) -> None:
    comparison = _comparison(seeded_session)
    comparison.review_decision = ComparisonReviewDecision.NEEDS_REVISION
    with pytest.raises(ImpactGenerationError) as review_error:
        generate_impact_explanation(
            seeded_session,
            comparison,
            provider=FakeImpactProvider(),
            created_by="admin",
        )
    assert review_error.value.code == "impact_comparison_not_approved"

    comparison.review_decision = ComparisonReviewDecision.APPROVE
    comparison.evidence_status = ComparisonEvidenceStatus.INCOMPLETE
    with pytest.raises(ImpactGenerationError) as evidence_error:
        generate_impact_explanation(
            seeded_session,
            comparison,
            provider=FakeImpactProvider(),
            created_by="admin",
        )
    assert evidence_error.value.code == "impact_evidence_not_verified"


def test_provider_configuration_is_explicit() -> None:
    with pytest.raises(ImpactGenerationError) as error:
        provider_from_settings(Settings(openai_api_key=None, ai_impact_model=None))
    assert error.value.code == "impact_provider_not_configured"

    provider = provider_from_settings(
        Settings(openai_api_key="test-key", ai_impact_model="test-model")
    )
    assert provider.provider_name == "openai"
    assert provider.model_name == "test-model"


def test_only_authenticated_admins_can_read_private_drafts(
    client: TestClient, seeded_session: Session
) -> None:
    comparison = _comparison(seeded_session)
    draft = generate_impact_explanation(
        seeded_session,
        comparison,
        provider=FakeImpactProvider(),
        created_by="reviewer",
    )
    seeded_session.commit()

    assert client.get(
        f"/api/admin/comparisons/{comparison.id}/impact-explanations"
    ).status_code == 401
    client.app.dependency_overrides[get_settings] = lambda: Settings(
        admin_username="reviewer",
        admin_password_hash=hash_admin_password(
            "correct horse battery staple", salt=b"test-salt-16byte"
        ),
        admin_session_secret="test-session-secret-with-sufficient-entropy",
    )
    assert client.post(
        "/api/admin/session",
        json={
            "username": "reviewer",
            "password": "correct horse battery staple",
        },
    ).status_code == 200
    response = client.get(
        f"/api/admin/comparisons/{comparison.id}/impact-explanations"
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["draft_id"] == draft.draft_id
    not_configured = client.post(
        f"/api/admin/comparisons/{comparison.id}/impact-explanations/generate",
        headers={"X-CMSQI-Admin-Action": "generate-impact-explanation"},
    )
    assert not_configured.status_code == 503
    assert not_configured.json()["code"] == "impact_provider_not_configured"
    assert "impact" not in client.get(
        "/api/changes/DEMO-001",
        params={
            "program": "Fictional Quality Program",
            "collection_type": "program_roster",
            "from_year": 2025,
            "to_year": 2026,
        },
    ).text.lower()
