import math

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.domain import CandidateReviewDecision, PublicationState
from app.models import (
    EvidenceReference,
    Measure,
    MeasureVersion,
    SourceRevision,
    SpecificationField,
    SpecificationFieldCandidate,
)
from app.schemas import (
    AdminCandidateReviewResponse,
    AdminFieldCandidateResponse,
    AdminMeasureDetail,
    AdminMeasurePage,
    AdminMeasureSummary,
    AdminMeasureVersionResponse,
    AdminMembershipResponse,
    AdminReviewSummary,
    PaginationMeta,
)
from app.services.publication import field_publication_eligibility, publication_blocker


def _has_review_candidates():
    return Measure.versions.any(MeasureVersion.field_candidates.any())


def review_summary(session: Session) -> AdminReviewSummary:
    return AdminReviewSummary(
        private_measures=session.scalar(
            select(func.count()).select_from(Measure).where(_has_review_candidates())
        )
        or 0,
        draft_versions=session.scalar(
            select(func.count())
            .select_from(MeasureVersion)
            .join(Measure)
            .where(
                _has_review_candidates(),
                MeasureVersion.publication_state == PublicationState.DRAFT,
            )
        )
        or 0,
        pending_candidates=session.scalar(
            select(func.count())
            .select_from(SpecificationFieldCandidate)
            .join(MeasureVersion)
            .join(Measure)
            .where(
                SpecificationFieldCandidate.review_decision
                == CandidateReviewDecision.PENDING
            )
        )
        or 0,
        decided_candidates=session.scalar(
            select(func.count())
            .select_from(SpecificationFieldCandidate)
            .join(MeasureVersion)
            .join(Measure)
            .where(
                SpecificationFieldCandidate.review_decision
                != CandidateReviewDecision.PENDING
            )
        )
        or 0,
        source_revisions=session.scalar(
            select(func.count())
            .select_from(SourceRevision)
            .where(
                or_(
                    SourceRevision.field_candidates.any(
                        SpecificationFieldCandidate.measure_version.has(
                            MeasureVersion.measure.has(_has_review_candidates())
                        )
                    ),
                    SourceRevision.evidence_references.any(
                        EvidenceReference.specification_field.has(
                            SpecificationField.measure_version.has(
                                MeasureVersion.measure.has(_has_review_candidates())
                            )
                        )
                    ),
                )
            )
        )
        or 0,
        newer_revision_flags=session.scalar(
            select(func.count())
            .select_from(MeasureVersion)
            .join(Measure)
            .where(
                _has_review_candidates(),
                MeasureVersion.newer_revision_detected.is_(True),
            )
        )
        or 0,
    )


def _private_measure_query():
    return (
        select(Measure)
        .where(_has_review_candidates())
        .options(
            selectinload(Measure.memberships),
            selectinload(Measure.versions)
            .selectinload(MeasureVersion.field_candidates)
            .selectinload(SpecificationFieldCandidate.source_revision)
            .selectinload(SourceRevision.source_document),
            selectinload(Measure.versions)
            .selectinload(MeasureVersion.field_candidates)
            .selectinload(SpecificationFieldCandidate.reviews),
            selectinload(Measure.versions)
            .selectinload(MeasureVersion.field_candidates)
            .selectinload(SpecificationFieldCandidate.published_field),
        )
    )


def _candidate_response(
    candidate: SpecificationFieldCandidate,
) -> AdminFieldCandidateResponse:
    revision = candidate.source_revision
    eligibility = field_publication_eligibility(candidate)
    return AdminFieldCandidateResponse(
        review_item_id=candidate.review_item_id,
        field_name=candidate.field_name,
        candidate_value=candidate.candidate_value,
        source_excerpt=candidate.source_excerpt,
        extraction_status=candidate.extraction_status,
        evidence_locator=candidate.evidence_locator,
        review_decision=candidate.review_decision,
        reviewed_value=candidate.reviewed_value,
        reviewer_name=candidate.reviewer_name,
        reviewed_at=candidate.reviewed_at,
        reviewer_notes=candidate.reviewer_notes,
        publication_state=candidate.publication_state,
        publication_eligibility=eligibility,
        publication_blocker=publication_blocker(eligibility),
        published_field=(
            candidate.published_field.field if candidate.published_field is not None else None
        ),
        published_at=candidate.published_at,
        published_by=candidate.published_by,
        source_id=revision.source_document.source_id,
        source_revision_id=revision.revision_id,
        source_title=revision.source_document.title,
        official_url=revision.source_document.official_url,
        source_content_hash=revision.content_hash,
        review_history=[
            AdminCandidateReviewResponse(
                decision=review.decision,
                reviewed_value=review.reviewed_value,
                reviewer_name=review.reviewer_name,
                reviewed_at=review.reviewed_at,
                reviewer_notes=review.reviewer_notes,
            )
            for review in sorted(candidate.reviews, key=lambda item: item.reviewed_at)
        ],
    )


def get_private_candidate(
    session: Session, review_item_id: str
) -> SpecificationFieldCandidate | None:
    return session.scalar(
        select(SpecificationFieldCandidate)
        .join(MeasureVersion)
        .join(Measure)
        .where(
            SpecificationFieldCandidate.review_item_id == review_item_id,
        )
        .options(
            selectinload(SpecificationFieldCandidate.source_revision).selectinload(
                SourceRevision.source_document
            ),
            selectinload(SpecificationFieldCandidate.measure_version),
            selectinload(SpecificationFieldCandidate.reviews),
            selectinload(SpecificationFieldCandidate.published_field),
        )
    )


def candidate_response(
    candidate: SpecificationFieldCandidate,
) -> AdminFieldCandidateResponse:
    return _candidate_response(candidate)


def _measure_summary(measure: Measure) -> AdminMeasureSummary:
    candidates = [
        candidate for version in measure.versions for candidate in version.field_candidates
    ]
    revisions = {candidate.source_revision for candidate in candidates}
    return AdminMeasureSummary(
        measure_id=measure.measure_id,
        name=measure.name,
        description=measure.description,
        performance_years=sorted(
            {
                membership.performance_year
                for membership in measure.memberships
                if membership.is_program_member
            }
        ),
        draft_versions=sum(
            version.publication_state == PublicationState.DRAFT for version in measure.versions
        ),
        pending_candidates=sum(
            candidate.review_decision == CandidateReviewDecision.PENDING
            for candidate in candidates
        ),
        decided_candidates=sum(
            candidate.review_decision != CandidateReviewDecision.PENDING
            for candidate in candidates
        ),
        source_documents=len({revision.source_document_id for revision in revisions}),
        newer_revision_detected=any(
            version.newer_revision_detected for version in measure.versions
        ),
        last_source_check_at=max(
            (version.last_source_check_at for version in measure.versions), default=None
        ),
    )


def list_private_measures(
    session: Session,
    *,
    q: str | None,
    page: int,
    page_size: int,
) -> AdminMeasurePage:
    statement = _private_measure_query()
    if q:
        pattern = f"%{q.strip()}%"
        statement = statement.where(
            or_(
                Measure.measure_id.ilike(pattern),
                Measure.name.ilike(pattern),
                Measure.description.ilike(pattern),
            )
        )
    total_items = session.scalar(
        select(func.count()).select_from(statement.with_only_columns(Measure.id).subquery())
    ) or 0
    measures = list(
        session.scalars(
            statement.order_by(Measure.measure_id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).unique()
    )
    return AdminMeasurePage(
        items=[_measure_summary(measure) for measure in measures],
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=math.ceil(total_items / page_size) if total_items else 0,
        ),
    )


def get_private_measure(session: Session, measure_id: str) -> AdminMeasureDetail | None:
    measure = session.scalar(
        _private_measure_query().where(Measure.measure_id == measure_id)
    )
    if measure is None:
        return None

    versions = []
    for version in sorted(
        measure.versions,
        key=lambda item: (item.performance_year, item.collection_type.value, item.version_id),
    ):
        candidates = []
        for candidate in sorted(
            version.field_candidates, key=lambda item: (item.field_name, item.review_item_id)
        ):
            candidates.append(_candidate_response(candidate))
        versions.append(
            AdminMeasureVersionResponse(
                version_id=version.version_id,
                performance_year=version.performance_year,
                program=version.program,
                collection_type=version.collection_type,
                specification_identifier=version.specification_identifier,
                publication_state=version.publication_state,
                verification_status=version.verification_status,
                newer_revision_detected=version.newer_revision_detected,
                last_source_check_at=version.last_source_check_at,
                candidates=candidates,
            )
        )
    return AdminMeasureDetail(
        measure_id=measure.measure_id,
        name=measure.name,
        description=measure.description,
        is_public=measure.is_public,
        memberships=[
            AdminMembershipResponse(
                performance_year=membership.performance_year,
                program=membership.program,
                is_program_member=membership.is_program_member,
                publication_state=membership.publication_state,
                verified_at=membership.verified_at,
            )
            for membership in sorted(
                measure.memberships, key=lambda item: item.performance_year
            )
        ],
        versions=versions,
    )
