"""Private comparison preparation and review projections."""

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain import (
    AffectedField,
    CollectionType,
    PublicationState,
)
from app.models import (
    EvidenceReference,
    Measure,
    MeasureComparison,
    MeasureComparisonEvidence,
    MeasureComparisonField,
    MeasureVersion,
    SourceRevision,
    SpecificationField,
)
from app.schemas import (
    AdminComparisonGenerationResponse,
    AdminComparisonPage,
    AdminComparisonResponse,
    AdminComparisonReviewResponse,
    ChangeFieldEvidenceResponse,
    ChangeFieldResponse,
)
from app.services.comparison_publication import (
    comparison_publication_blocker,
    comparison_publication_eligibility,
)
from app.services.deterministic_comparison import generate_draft_comparison


def _comparison_options():
    links = selectinload(MeasureComparison.affected_fields).selectinload(
        MeasureComparisonField.evidence_links
    )
    references = links.selectinload(MeasureComparisonEvidence.evidence_reference)
    return (
        selectinload(MeasureComparison.measure),
        selectinload(MeasureComparison.reviews),
        references.selectinload(EvidenceReference.source_revision).selectinload(
            SourceRevision.source_document
        ),
        references.selectinload(EvidenceReference.specification_field).selectinload(
            SpecificationField.measure_version
        ),
    )


def get_admin_comparison(
    session: Session, comparison_id: int
) -> MeasureComparison | None:
    return session.scalar(
        select(MeasureComparison)
        .where(MeasureComparison.id == comparison_id)
        .options(*_comparison_options())
    )


def _evidence_response(link: MeasureComparisonEvidence) -> ChangeFieldEvidenceResponse:
    reference = link.evidence_reference
    revision = reference.source_revision
    return ChangeFieldEvidenceResponse(
        evidence_id=reference.evidence_id,
        source_revision_id=revision.revision_id,
        document_title=revision.source_document.title,
        official_url=revision.source_document.official_url,
        locator=reference.locator,
        excerpt=reference.excerpt,
        side=link.side,
    )


def admin_comparison_response(
    comparison: MeasureComparison,
) -> AdminComparisonResponse:
    eligibility = comparison_publication_eligibility(comparison)
    return AdminComparisonResponse(
        comparison_id=comparison.id,
        measure_id=comparison.measure.measure_id,
        measure_name=comparison.measure.name,
        program=comparison.program,
        collection_type=comparison.collection_type,
        from_year=comparison.from_year,
        to_year=comparison.to_year,
        status=comparison.status,
        evidence_status=comparison.evidence_status,
        publication_state=comparison.publication_state,
        publication_eligibility=eligibility,
        publication_blocker=comparison_publication_blocker(eligibility),
        review_decision=comparison.review_decision,
        reviewed_at=comparison.reviewed_at,
        reviewer_name=comparison.reviewer_name,
        reviewer_notes=comparison.reviewer_notes,
        published_at=comparison.published_at,
        published_by=comparison.published_by,
        created_at=comparison.created_at,
        fields=[
            ChangeFieldResponse(
                field=field.field,
                status=field.status,
                from_availability=field.from_availability,
                to_availability=field.to_availability,
                from_value=field.from_value,
                to_value=field.to_value,
                evidence=[
                    _evidence_response(link)
                    for link in sorted(
                        field.evidence_links,
                        key=lambda item: (
                            item.side.value,
                            item.evidence_reference.evidence_id,
                        ),
                    )
                ],
            )
            for field in sorted(
                comparison.affected_fields, key=lambda item: item.field.value
            )
        ],
        review_history=[
            AdminComparisonReviewResponse(
                decision=review.decision,
                reviewer_name=review.reviewer_name,
                reviewed_at=review.reviewed_at,
                reviewer_notes=review.reviewer_notes,
            )
            for review in sorted(comparison.reviews, key=lambda item: item.reviewed_at)
        ],
    )


def list_admin_comparisons(
    session: Session,
    *,
    from_year: int,
    to_year: int,
    collection_type: CollectionType,
) -> AdminComparisonPage:
    comparisons = session.scalars(
        select(MeasureComparison)
        .where(
            MeasureComparison.from_year == from_year,
            MeasureComparison.to_year == to_year,
            MeasureComparison.collection_type == collection_type,
        )
        .options(*_comparison_options())
        .order_by(MeasureComparison.measure_id, MeasureComparison.program)
    ).unique()
    return AdminComparisonPage(items=[admin_comparison_response(item) for item in comparisons])


def prepare_roster_comparisons(
    session: Session,
    *,
    from_year: int,
    to_year: int,
) -> AdminComparisonGenerationResponse:
    versions = session.scalars(
        select(MeasureVersion)
        .where(
            MeasureVersion.performance_year.in_((from_year, to_year)),
            MeasureVersion.collection_type == CollectionType.PROGRAM_ROSTER,
            MeasureVersion.publication_state == PublicationState.PUBLISHED,
            MeasureVersion.verified_at.is_not(None),
            MeasureVersion.newer_revision_detected.is_(False),
        )
        .options(selectinload(MeasureVersion.measure))
        .order_by(MeasureVersion.measure_id, MeasureVersion.program)
    ).unique()
    grouped: dict[tuple[str, str], set[int]] = defaultdict(set)
    for version in versions:
        grouped[(version.measure.measure_id, version.program)].add(
            version.performance_year
        )

    prepared = 0
    existing = 0
    skipped: list[str] = []
    for (measure_id, program), years in sorted(grouped.items()):
        if years != {from_year, to_year}:
            skipped.append(measure_id)
            continue
        current = session.scalar(
            select(MeasureComparison.id)
            .join(MeasureComparison.measure)
            .where(
                Measure.measure_id == measure_id,
                MeasureComparison.program == program,
                MeasureComparison.from_year == from_year,
                MeasureComparison.to_year == to_year,
                MeasureComparison.collection_type == CollectionType.PROGRAM_ROSTER,
            )
        )
        if current is not None:
            existing += 1
            continue
        generate_draft_comparison(
            session,
            measure_id=measure_id,
            program=program,
            from_year=from_year,
            to_year=to_year,
            collection_type=CollectionType.PROGRAM_ROSTER,
            fields=(AffectedField.MEASURE_SET,),
        )
        prepared += 1
    session.flush()
    return AdminComparisonGenerationResponse(
        prepared=prepared,
        existing=existing,
        skipped_measure_ids=sorted(set(skipped)),
    )
