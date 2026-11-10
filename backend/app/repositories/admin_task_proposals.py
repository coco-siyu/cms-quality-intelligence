"""Private read model for generated impact task proposals."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    EvidenceReference,
    ImpactExplanationDraft,
    MeasureComparisonEvidence,
    ReviewTaskProposal,
    ReviewTaskProposalCitation,
    SourceRevision,
)
from app.schemas import (
    AdminImpactTaskProposalPage,
    AdminImpactTaskProposalResponse,
    ChangeFieldEvidenceResponse,
)


def _proposal_options():
    evidence = (
        selectinload(ReviewTaskProposal.citations)
        .selectinload(ReviewTaskProposalCitation.comparison_evidence)
        .selectinload(MeasureComparisonEvidence.evidence_reference)
    )
    return (
        selectinload(ReviewTaskProposal.review),
        selectinload(ReviewTaskProposal.impact_explanation_draft),
        evidence.selectinload(EvidenceReference.source_revision).selectinload(
            SourceRevision.source_document
        ),
    )


def list_task_proposal_models(
    session: Session,
    *,
    draft_id: str,
) -> list[ReviewTaskProposal] | None:
    draft = session.scalar(
        select(ImpactExplanationDraft).where(ImpactExplanationDraft.draft_id == draft_id)
    )
    if draft is None:
        return None
    return list(
        session.scalars(
            select(ReviewTaskProposal)
            .where(ReviewTaskProposal.impact_explanation_draft_id == draft.id)
            .options(*_proposal_options())
            .order_by(ReviewTaskProposal.sequence)
        ).all()
    )


def _evidence_response(
    citation: ReviewTaskProposalCitation,
) -> ChangeFieldEvidenceResponse:
    link = citation.comparison_evidence
    reference = link.evidence_reference
    revision = reference.source_revision
    return ChangeFieldEvidenceResponse(
        evidence_id=reference.evidence_id,
        source_revision_id=revision.revision_id,
        document_title=revision.source_document.title,
        official_url=revision.source_document.official_url,
        publication_date=revision.publication_date,
        effective_date=revision.effective_date,
        locator=reference.locator,
        excerpt=reference.excerpt,
        side=link.side,
    )


def task_proposal_response(
    proposal: ReviewTaskProposal,
) -> AdminImpactTaskProposalResponse:
    return AdminImpactTaskProposalResponse(
        proposal_id=proposal.proposal_id,
        review_id=proposal.review.review_id,
        impact_explanation_draft_id=proposal.impact_explanation_draft.draft_id,
        sequence=proposal.sequence,
        role=proposal.role,
        title=proposal.title,
        description=proposal.description,
        status=proposal.status,
        evidence=[
            _evidence_response(citation)
            for citation in sorted(
                proposal.citations,
                key=lambda item: item.comparison_evidence.evidence_reference.evidence_id,
            )
        ],
        provider=proposal.provider,
        model=proposal.model,
        prompt_version=proposal.prompt_version,
        input_digest=proposal.input_digest,
        provider_response_id=proposal.provider_response_id,
        decided_at=proposal.decided_at,
        decided_by=proposal.decided_by,
        created_at=proposal.created_at,
        created_by=proposal.created_by,
    )


def task_proposal_page(
    proposals: list[ReviewTaskProposal],
) -> AdminImpactTaskProposalPage:
    return AdminImpactTaskProposalPage(
        items=[task_proposal_response(proposal) for proposal in proposals]
    )
