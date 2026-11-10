from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import hash_admin_password
from app.config import Settings, get_settings
from app.domain import (
    ImpactExplanationReviewDecision,
    ReviewEventType,
    ReviewRole,
    TaskProposalStatus,
)
from app.models import (
    ImpactExplanationDraft,
    MeasureComparison,
    MeasureReview,
    ReviewEvent,
    ReviewTaskProposal,
)
from app.repositories.admin_task_proposals import list_task_proposal_models
from app.services.ai_impact_explanation import ImpactComparisonInput
from app.services.ai_impact_task_proposals import (
    ImpactTaskGenerationError,
    ImpactTaskProposalProvider,
    ImpactTaskProviderResult,
    generate_impact_task_proposals,
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
from app.services.impact_task_proposals import (
    ImpactTaskCitation,
    ImpactTaskProposal,
    ImpactTaskProposalOutput,
)
from app.services.semantic_classification import SemanticEvidenceExcerpt


class FakeTaskProvider(ImpactTaskProposalProvider):
    provider_name = "test-provider"
    model_name = "test-task-model"

    def __init__(self, *, unsupported: bool = False) -> None:
        self.calls = 0
        self.unsupported = unsupported

    def generate(
        self,
        *,
        comparison: ImpactComparisonInput,
        approved_explanation: ImpactExplanationOutput,
        evidence: list[SemanticEvidenceExcerpt],
    ) -> ImpactTaskProviderResult:
        self.calls += 1
        assert comparison.measure_id == "DEMO-001"
        assert approved_explanation.plain_language_summary.statement_type == "source_fact"
        evidence_ids = [item.evidence_id for item in evidence]
        first_evidence = "NOT-SUPPLIED" if self.unsupported else evidence_ids[0]
        return ImpactTaskProviderResult(
            output=ImpactTaskProposalOutput(
                proposals=[
                    ImpactTaskProposal(
                        role=ReviewRole.DATA_ANALYST,
                        title="Review the year-specific data mapping",
                        description=(
                            "Consider validating the fictional reporting mapping against "
                            "the approved year-specific definition."
                        ),
                        citations=[ImpactTaskCitation(evidence_id=first_evidence)],
                    ),
                    ImpactTaskProposal(
                        role=ReviewRole.ACO_QUALITY_MANAGER,
                        title="Confirm the reporting workflow handoff",
                        description=(
                            "Consider confirming that the fictional operational workflow "
                            "uses the approved performance-year definition."
                        ),
                        citations=[ImpactTaskCitation(evidence_id=evidence_ids[-1])],
                    ),
                ]
            ),
            response_id="task-response-001",
        )


def _comparison(session: Session) -> MeasureComparison:
    comparison = session.scalar(
        select(MeasureComparison).where(MeasureComparison.measure.has(measure_id="DEMO-001"))
    )
    assert comparison is not None
    return comparison


def _approved_output(comparison: MeasureComparison) -> ImpactExplanationOutput:
    evidence_ids = sorted(
        link.evidence_reference.evidence_id
        for field in comparison.affected_fields
        for link in field.evidence_links
    )
    implication = ImpactStatement(
        statement="A team may need to review this fictional year-specific change.",
        statement_type=ImpactStatementType.POSSIBLE_IMPACT,
        citations=[ImpactCitation(evidence_id=evidence_ids[0])],
    )
    return ImpactExplanationOutput(
        plain_language_summary=ImpactStatement(
            statement="The two fictional year-specific definitions differ.",
            statement_type=ImpactStatementType.SOURCE_FACT,
            citations=[ImpactCitation(evidence_id=item) for item in evidence_ids],
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
    )


def _approved_draft(
    session: Session,
    *,
    sequence: int = 1,
    outdated: bool = False,
) -> ImpactExplanationDraft:
    comparison = _comparison(session)
    output = _approved_output(comparison)
    reviewed_at = datetime(2026, 11, 10, 14, tzinfo=UTC)
    draft = ImpactExplanationDraft(
        draft_id=f"TASK-PROPOSAL-DRAFT-{sequence}",
        comparison=comparison,
        provider="test-provider",
        model="test-impact-model",
        prompt_version="impact-v1",
        input_digest=f"impact-digest-{sequence}",
        generation_sequence=sequence,
        output_payload=output.model_dump(mode="json"),
        review_decision=ImpactExplanationReviewDecision.APPROVE,
        approved_output_payload=output.model_dump(mode="json"),
        reviewed_at=reviewed_at,
        reviewed_by="reviewer",
        outdated_at=reviewed_at if outdated else None,
        created_by="generator",
    )
    session.add(draft)
    session.commit()
    return draft


def test_generation_persists_idempotent_role_tagged_cited_proposals(
    seeded_session: Session,
) -> None:
    draft = _approved_draft(seeded_session)
    provider = FakeTaskProvider()

    first = generate_impact_task_proposals(
        seeded_session,
        draft,
        provider=provider,
        created_by="admin",
    )
    repeated = generate_impact_task_proposals(
        seeded_session,
        draft,
        provider=provider,
        created_by="admin",
    )
    seeded_session.commit()

    assert [item.id for item in repeated] == [item.id for item in first]
    assert provider.calls == 1
    assert [item.role for item in first] == [
        ReviewRole.DATA_ANALYST,
        ReviewRole.ACO_QUALITY_MANAGER,
    ]
    assert all(item.status == TaskProposalStatus.PENDING for item in first)
    assert all(item.prompt_version == "cms-impact-task-proposals-v1" for item in first)
    assert all(len(item.input_digest) == 64 for item in first)
    assert all(item.provider_response_id == "task-response-001" for item in first)
    assert [len(item.citations) for item in first] == [1, 1]

    review = seeded_session.scalar(select(MeasureReview))
    assert review is not None
    assert review.checklist_items == []
    events = seeded_session.scalars(select(ReviewEvent).order_by(ReviewEvent.sequence)).all()
    assert [event.event_type for event in events] == [
        ReviewEventType.REVIEW_CREATED,
        ReviewEventType.PROPOSAL_CREATED,
        ReviewEventType.PROPOSAL_CREATED,
    ]


def test_new_explanation_version_gets_separate_proposals(
    seeded_session: Session,
) -> None:
    first_draft = _approved_draft(seeded_session, sequence=1)
    provider = FakeTaskProvider()
    first = generate_impact_task_proposals(
        seeded_session,
        first_draft,
        provider=provider,
        created_by="admin",
    )
    seeded_session.commit()

    second_draft = _approved_draft(seeded_session, sequence=2)
    second = generate_impact_task_proposals(
        seeded_session,
        second_draft,
        provider=provider,
        created_by="admin",
    )
    seeded_session.commit()

    assert provider.calls == 2
    assert {item.impact_explanation_draft_id for item in first} == {first_draft.id}
    assert {item.impact_explanation_draft_id for item in second} == {second_draft.id}
    assert seeded_session.query(ReviewTaskProposal).count() == 4
    assert seeded_session.query(MeasureReview).count() == 1


def test_generation_rejects_unapproved_outdated_and_unsupported_inputs(
    seeded_session: Session,
) -> None:
    unapproved = _approved_draft(seeded_session, sequence=1)
    unapproved.review_decision = ImpactExplanationReviewDecision.PENDING
    unapproved.approved_output_payload = None
    unapproved.reviewed_at = None
    unapproved.reviewed_by = None
    seeded_session.commit()

    provider = FakeTaskProvider()
    with pytest.raises(ImpactTaskGenerationError) as approval_error:
        generate_impact_task_proposals(
            seeded_session,
            unapproved,
            provider=provider,
            created_by="admin",
        )
    assert approval_error.value.code == "task_proposal_explanation_not_approved"

    outdated = _approved_draft(seeded_session, sequence=2, outdated=True)
    with pytest.raises(ImpactTaskGenerationError) as outdated_error:
        generate_impact_task_proposals(
            seeded_session,
            outdated,
            provider=provider,
            created_by="admin",
        )
    assert outdated_error.value.code == "task_proposal_explanation_outdated"

    current = _approved_draft(seeded_session, sequence=3)
    with pytest.raises(ImpactTaskGenerationError) as citation_error:
        generate_impact_task_proposals(
            seeded_session,
            current,
            provider=FakeTaskProvider(unsupported=True),
            created_by="admin",
        )
    assert citation_error.value.code == "task_proposal_citation_unsupported"
    assert seeded_session.query(ReviewTaskProposal).count() == 0


def test_contract_rejects_production_sql() -> None:
    with pytest.raises(ValidationError):
        ImpactTaskProposal(
            role=ReviewRole.DATA_ANALYST,
            title="Build the report",
            description="SELECT patient_id FROM production_table",
            citations=[ImpactTaskCitation(evidence_id="EVIDENCE-1")],
        )


def test_provider_configuration_is_explicit() -> None:
    with pytest.raises(ImpactTaskGenerationError) as error:
        provider_from_settings(Settings(openai_api_key=None, ai_impact_model=None))
    assert error.value.code == "task_proposal_provider_not_configured"

    provider = provider_from_settings(
        Settings(openai_api_key="test-key", ai_impact_model="test-model")
    )
    assert provider.provider_name == "openai"
    assert provider.model_name == "test-model"


def test_admin_generation_and_listing_are_private(
    client: TestClient,
    seeded_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    draft = _approved_draft(seeded_session)
    collection_path = f"/api/admin/impact-explanations/{draft.draft_id}/task-proposals"

    assert client.get(collection_path).status_code == 401
    assert (
        client.post(
            f"{collection_path}/generate",
            headers={"X-CMSQI-Admin-Action": "generate-task-proposals"},
        ).status_code
        == 401
    )

    client.app.dependency_overrides[get_settings] = lambda: Settings(
        admin_username="reviewer",
        admin_password_hash=hash_admin_password(
            "correct horse battery staple", salt=b"test-salt-16byte"
        ),
        admin_session_secret="test-session-secret-with-sufficient-entropy",
        openai_api_key="test-key",
        ai_impact_model="test-model",
    )
    assert (
        client.post(
            "/api/admin/session",
            json={"username": "reviewer", "password": "correct horse battery staple"},
        ).status_code
        == 200
    )
    monkeypatch.setattr(
        "app.api.admin.task_proposal_provider_from_settings",
        lambda _settings: FakeTaskProvider(),
    )

    wrong_header = client.post(
        f"{collection_path}/generate",
        headers={"X-CMSQI-Admin-Action": "generate-impact-explanation"},
    )
    assert wrong_header.status_code == 403

    generated = client.post(
        f"{collection_path}/generate",
        headers={"X-CMSQI-Admin-Action": "generate-task-proposals"},
    )
    assert generated.status_code == 200
    assert [item["role"] for item in generated.json()["items"]] == [
        "data_analyst",
        "aco_quality_manager",
    ]
    assert all(item["status"] == "pending" for item in generated.json()["items"])
    assert all(item["evidence"] for item in generated.json()["items"])

    listed = client.get(collection_path)
    assert listed.status_code == 200
    assert listed.json() == generated.json()
    assert list_task_proposal_models(seeded_session, draft_id="DOES-NOT-EXIST") is None
