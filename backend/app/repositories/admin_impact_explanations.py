"""Private read model for generated impact-explanation drafts."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    ImpactExplanationCitation,
    ImpactExplanationDraft,
    MeasureComparisonEvidence,
)
from app.schemas import (
    AdminImpactExplanationDraftPage,
    AdminImpactExplanationDraftResponse,
)
from app.services.impact_explanation import ImpactExplanationOutput


def impact_draft_response(
    draft: ImpactExplanationDraft,
) -> AdminImpactExplanationDraftResponse:
    return AdminImpactExplanationDraftResponse(
        draft_id=draft.draft_id,
        comparison_id=draft.comparison_id,
        provider=draft.provider,
        model=draft.model,
        prompt_version=draft.prompt_version,
        input_digest=draft.input_digest,
        output=ImpactExplanationOutput.model_validate(draft.output_payload),
        cited_evidence_ids=sorted(
            citation.comparison_evidence.evidence_reference.evidence_id
            for citation in draft.citations
        ),
        provider_response_id=draft.provider_response_id,
        created_at=draft.created_at,
        created_by=draft.created_by,
    )


def list_impact_explanation_drafts(
    session: Session,
    *,
    comparison_id: int,
) -> AdminImpactExplanationDraftPage:
    drafts = session.scalars(
        select(ImpactExplanationDraft)
        .where(ImpactExplanationDraft.comparison_id == comparison_id)
        .options(
            selectinload(ImpactExplanationDraft.citations)
            .selectinload(ImpactExplanationCitation.comparison_evidence)
            .selectinload(MeasureComparisonEvidence.evidence_reference)
        )
        .order_by(ImpactExplanationDraft.created_at.desc(), ImpactExplanationDraft.id.desc())
    ).all()
    return AdminImpactExplanationDraftPage(
        items=[impact_draft_response(draft) for draft in drafts]
    )
