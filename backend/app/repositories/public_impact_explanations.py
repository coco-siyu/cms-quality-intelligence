"""Fail-closed public projection for approved role-specific explanations."""

from datetime import UTC, datetime

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain import (
    CollectionType,
    ImpactExplanationReviewDecision,
    PublicationState,
)
from app.models import (
    EvidenceReference,
    ImpactExplanationCitation,
    ImpactExplanationDraft,
    Measure,
    MeasureComparison,
    MeasureComparisonEvidence,
    MeasureComparisonField,
    SourceRevision,
    SpecificationField,
)
from app.schemas import ChangeFieldEvidenceResponse, PublicImpactExplanation
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


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _evidence_response(link: MeasureComparisonEvidence) -> ChangeFieldEvidenceResponse:
    reference = link.evidence_reference
    revision = reference.source_revision
    document = revision.source_document
    return ChangeFieldEvidenceResponse(
        evidence_id=reference.evidence_id,
        source_revision_id=revision.revision_id,
        document_title=document.title,
        official_url=document.official_url,
        publication_date=revision.publication_date,
        effective_date=revision.effective_date,
        locator=reference.locator,
        excerpt=reference.excerpt,
        side=link.side,
    )


def get_public_impact_explanation(
    session: Session,
    *,
    measure_id: str,
    program: str,
    collection_type: CollectionType,
    from_year: int,
    to_year: int,
) -> PublicImpactExplanation | None:
    """Return the newest current approved pair, never a generation draft."""

    comparison_loader = selectinload(ImpactExplanationDraft.comparison)
    field_links = comparison_loader.selectinload(MeasureComparison.affected_fields).selectinload(
        MeasureComparisonField.evidence_links
    )
    link_references = field_links.selectinload(MeasureComparisonEvidence.evidence_reference)
    draft_citations = selectinload(ImpactExplanationDraft.citations).selectinload(
        ImpactExplanationCitation.comparison_evidence
    )
    citation_references = draft_citations.selectinload(
        MeasureComparisonEvidence.evidence_reference
    )
    drafts = session.scalars(
        select(ImpactExplanationDraft)
        .join(ImpactExplanationDraft.comparison)
        .join(MeasureComparison.measure)
        .where(
            Measure.measure_id == measure_id,
            MeasureComparison.program == program,
            MeasureComparison.collection_type == collection_type,
            MeasureComparison.from_year == from_year,
            MeasureComparison.to_year == to_year,
            ImpactExplanationDraft.review_decision
            == ImpactExplanationReviewDecision.APPROVE,
            ImpactExplanationDraft.publication_state == PublicationState.PUBLISHED,
            ImpactExplanationDraft.outdated_at.is_(None),
        )
        .options(
            comparison_loader.selectinload(MeasureComparison.measure),
            field_links,
            link_references.selectinload(EvidenceReference.source_revision).selectinload(
                SourceRevision.source_document
            ),
            link_references.selectinload(EvidenceReference.specification_field).selectinload(
                SpecificationField.measure_version
            ),
            citation_references.selectinload(EvidenceReference.source_revision).selectinload(
                SourceRevision.source_document
            ),
        )
        .order_by(
            ImpactExplanationDraft.published_at.desc(),
            ImpactExplanationDraft.id.desc(),
        )
    ).unique()

    for draft in drafts:
        comparison = draft.comparison
        if (
            draft.approved_output_payload is None
            or draft.reviewed_at is None
            or not draft.reviewed_by
            or draft.published_at is None
            or not draft.published_by
            or build_public_change_record(comparison) is None
        ):
            continue
        try:
            current_input, current_evidence, _ = build_impact_generation_input(comparison)
            if draft.input_digest != compute_impact_input_digest(
                current_input, current_evidence
            ):
                continue
            output = ImpactExplanationOutput.model_validate(draft.approved_output_payload)
            validate_impact_citations(output, current_evidence)
        except (
            ImpactGenerationError,
            ImpactExplanationValidationError,
            ValidationError,
        ):
            continue

        links_by_id = {
            citation.comparison_evidence.evidence_reference.evidence_id:
                citation.comparison_evidence
            for citation in draft.citations
        }
        cited_ids = {
            citation.evidence_id
            for statement in (
                output.plain_language_summary,
                *output.data_analyst.technical_implications,
                *output.data_analyst.validation_considerations,
                *output.aco_quality_manager.operational_implications,
                *output.aco_quality_manager.coordination_considerations,
            )
            for citation in statement.citations
        }
        cited_ids.update(
            citation.evidence_id
            for caveat in output.uncertainty_caveats
            for citation in caveat.citations
        )
        if not cited_ids.issubset(links_by_id):
            continue

        return PublicImpactExplanation(
            measure_id=comparison.measure.measure_id,
            measure_name=comparison.measure.name,
            program=comparison.program,
            collection_type=comparison.collection_type,
            from_year=comparison.from_year,
            to_year=comparison.to_year,
            approved_at=_as_utc(draft.reviewed_at),
            published_at=_as_utc(draft.published_at),
            output=output,
            evidence=[_evidence_response(links_by_id[item]) for item in sorted(cited_ids)],
        )
    return None
