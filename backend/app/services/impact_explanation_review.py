"""Human review and explicit publication for impact-explanation pairs."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import ImpactExplanationReviewDecision, PublicationState
from app.models import ImpactExplanationDraft
from app.services.ai_impact_explanation import (
    ImpactGenerationError,
    build_impact_generation_input,
    compute_impact_input_digest,
)
from app.services.comparison_evidence import build_public_change_record
from app.services.impact_explanation import (
    ImpactExplanationOutput,
    ImpactExplanationValidationError,
    validate_impact_citations,
)


class ImpactExplanationReviewError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _current_evidence(draft: ImpactExplanationDraft):
    try:
        comparison, evidence, _ = build_impact_generation_input(draft.comparison)
    except ImpactGenerationError as error:
        raise ImpactExplanationReviewError(error.code, error.message) from error
    if draft.input_digest != compute_impact_input_digest(comparison, evidence):
        raise ImpactExplanationReviewError(
            "impact_draft_input_outdated",
            "The approved comparison or its evidence changed after this draft was generated.",
        )
    return evidence


def _validate_reviewed_output(
    draft: ImpactExplanationDraft,
    output: ImpactExplanationOutput,
) -> ImpactExplanationOutput:
    evidence = _current_evidence(draft)
    try:
        validated = validate_impact_citations(output, evidence)
    except ImpactExplanationValidationError as error:
        raise ImpactExplanationReviewError(error.code, error.message) from error

    allowed_ids = {
        citation.comparison_evidence.evidence_reference.evidence_id
        for citation in draft.citations
    }
    cited_ids = {
        citation.evidence_id
        for statement in (
            validated.plain_language_summary,
            *validated.data_analyst.technical_implications,
            *validated.data_analyst.validation_considerations,
            *validated.aco_quality_manager.operational_implications,
            *validated.aco_quality_manager.coordination_considerations,
        )
        for citation in statement.citations
    }
    cited_ids.update(
        citation.evidence_id
        for caveat in validated.uncertainty_caveats
        for citation in caveat.citations
    )
    if not cited_ids.issubset(allowed_ids):
        raise ImpactExplanationReviewError(
            "impact_review_citation_not_in_draft",
            "Reviewed wording may only retain evidence citations attached to this draft.",
        )
    return validated


def record_impact_explanation_review(
    draft: ImpactExplanationDraft,
    *,
    decision: ImpactExplanationReviewDecision,
    output: ImpactExplanationOutput | None,
    reviewer_name: str,
    reviewed_at: datetime | None = None,
) -> ImpactExplanationDraft:
    """Record one final decision without changing the generated payload."""

    if draft.publication_state != PublicationState.DRAFT:
        raise ImpactExplanationReviewError(
            "impact_explanation_published_locked",
            "A published explanation version is immutable.",
        )
    if draft.review_decision != ImpactExplanationReviewDecision.PENDING:
        raise ImpactExplanationReviewError(
            "impact_explanation_review_locked",
            "This explanation version already has a final review decision.",
        )
    if draft.outdated_at is not None:
        raise ImpactExplanationReviewError(
            "impact_explanation_outdated",
            "This explanation cites an older source revision and must be regenerated.",
        )
    if decision == ImpactExplanationReviewDecision.PENDING:
        raise ImpactExplanationReviewError(
            "impact_explanation_review_invalid",
            "A review must approve or reject the complete role-specific pair.",
        )

    review_time = reviewed_at or datetime.now(UTC)
    if decision == ImpactExplanationReviewDecision.APPROVE:
        if output is None:
            raise ImpactExplanationReviewError(
                "impact_explanation_output_required",
                "Approval requires the complete reviewed explanation pair.",
            )
        approved = _validate_reviewed_output(draft, output)
        draft.approved_output_payload = approved.model_dump(mode="json")
    else:
        if output is not None:
            raise ImpactExplanationReviewError(
                "impact_explanation_rejection_output_forbidden",
                "Rejected drafts cannot store approved wording.",
            )
        _current_evidence(draft)
        draft.approved_output_payload = None

    draft.review_decision = decision
    draft.reviewed_at = review_time
    draft.reviewed_by = reviewer_name
    return draft


def publish_approved_impact_explanation(
    session: Session,
    draft: ImpactExplanationDraft,
    *,
    publisher_name: str,
    published_at: datetime | None = None,
) -> ImpactExplanationDraft:
    """Publish one current approved pair and retire the previous public pair."""

    if draft.publication_state == PublicationState.PUBLISHED:
        return draft
    if draft.publication_state == PublicationState.WITHDRAWN:
        raise ImpactExplanationReviewError(
            "impact_explanation_withdrawn_locked",
            "A withdrawn explanation version cannot be published again.",
        )
    if (
        draft.review_decision != ImpactExplanationReviewDecision.APPROVE
        or draft.approved_output_payload is None
        or draft.reviewed_at is None
        or not draft.reviewed_by
    ):
        raise ImpactExplanationReviewError(
            "impact_explanation_not_approved",
            "Review and approve both role-specific explanations before publication.",
        )
    if draft.outdated_at is not None:
        raise ImpactExplanationReviewError(
            "impact_explanation_outdated",
            "This explanation cites an older source revision and cannot be published.",
        )
    if build_public_change_record(draft.comparison) is None:
        raise ImpactExplanationReviewError(
            "impact_comparison_not_public",
            "Publish the current approved comparison before its explanation.",
        )

    output = ImpactExplanationOutput.model_validate(draft.approved_output_payload)
    _validate_reviewed_output(draft, output)
    publication_time = published_at or datetime.now(UTC)

    previous = session.scalars(
        select(ImpactExplanationDraft).where(
            ImpactExplanationDraft.comparison_id == draft.comparison_id,
            ImpactExplanationDraft.id != draft.id,
            ImpactExplanationDraft.publication_state == PublicationState.PUBLISHED,
        )
    ).all()
    for item in previous:
        item.publication_state = PublicationState.WITHDRAWN

    draft.publication_state = PublicationState.PUBLISHED
    draft.published_at = publication_time
    draft.published_by = publisher_name
    session.flush()
    return draft
