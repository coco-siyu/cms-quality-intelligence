import math
from dataclasses import dataclass

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.domain import (
    AffectedField,
    ChangeStatus,
    PublicationState,
    PublicVerificationStatus,
)
from app.models import (
    EvidenceReference,
    Measure,
    MeasureComparison,
    MeasureComparisonField,
    MeasureVersion,
    ProgramMembership,
    SourceRevision,
    SpecificationField,
)
from app.schemas import (
    EvidenceReferenceResponse,
    FreshnessResponse,
    MeasureVersionResponse,
    PaginationMeta,
    PublicMeasureDetail,
    PublicMeasurePage,
    PublicMeasureSummary,
    SpecificationFieldResponse,
)


@dataclass(frozen=True)
class MeasureFilters:
    q: str | None = None
    performance_year: int | None = None
    from_year: int | None = None
    to_year: int | None = None
    change_status: ChangeStatus | None = None
    affected_field: AffectedField | None = None
    verification_status: PublicVerificationStatus | None = None
    page: int = 1
    page_size: int = 25


def _public_versions_query() -> Select[tuple[MeasureVersion]]:
    return (
        select(MeasureVersion)
        .where(MeasureVersion.publication_state == PublicationState.PUBLISHED)
        .options(
            selectinload(MeasureVersion.fields)
            .selectinload(SpecificationField.evidence)
            .selectinload(EvidenceReference.source_revision)
            .selectinload(SourceRevision.source_document)
        )
    )


def _versions_for_measure(
    session: Session,
    measure_pk: int,
    years: set[int] | None = None,
) -> list[MeasureVersion]:
    statement = _public_versions_query().where(MeasureVersion.measure_id == measure_pk)
    if years:
        statement = statement.where(MeasureVersion.performance_year.in_(years))
    return list(
        session.scalars(
            statement.order_by(
                MeasureVersion.performance_year, MeasureVersion.version_number.desc()
            )
        ).unique()
    )


def _published_comparison(
    session: Session,
    measure_pk: int,
    from_year: int | None,
    to_year: int | None,
) -> MeasureComparison | None:
    statement = (
        select(MeasureComparison)
        .where(
            MeasureComparison.measure_id == measure_pk,
            MeasureComparison.publication_state == PublicationState.PUBLISHED,
        )
        .options(selectinload(MeasureComparison.affected_fields))
    )
    if from_year is not None:
        statement = statement.where(MeasureComparison.from_year == from_year)
    if to_year is not None:
        statement = statement.where(MeasureComparison.to_year == to_year)
    return session.scalar(statement.order_by(MeasureComparison.to_year.desc()).limit(1))


def _freshness(versions: list[MeasureVersion]) -> FreshnessResponse:
    if not versions:
        raise ValueError("A public measure projection requires a published version")
    severity = {
        PublicVerificationStatus.VERIFIED: 0,
        PublicVerificationStatus.PARTIALLY_VERIFIED: 1,
        PublicVerificationStatus.SOURCE_UPDATE_DETECTED: 2,
    }
    status = max((version.verification_status for version in versions), key=severity.get)
    verified_values = [version.verified_at for version in versions if version.verified_at]
    return FreshnessResponse(
        last_verified_at=max(verified_values) if verified_values else None,
        last_source_check_at=max(version.last_source_check_at for version in versions),
        verification_status=status,
        newer_revision_detected=any(version.newer_revision_detected for version in versions),
    )


def _field_response(field: SpecificationField) -> SpecificationFieldResponse:
    evidence = []
    for reference in field.evidence:
        revision = reference.source_revision
        if revision.publication_state != PublicationState.PUBLISHED:
            continue
        evidence.append(
            EvidenceReferenceResponse(
                evidence_id=reference.evidence_id,
                source_revision_id=revision.revision_id,
                document_title=revision.source_document.title,
                official_url=revision.source_document.official_url,
                locator=reference.locator,
                excerpt=reference.excerpt,
            )
        )
    return SpecificationFieldResponse(
        field=field.field,
        availability=field.availability,
        value=field.value,
        evidence=evidence,
    )


def _version_response(version: MeasureVersion) -> MeasureVersionResponse:
    return MeasureVersionResponse(
        version_id=version.version_id,
        performance_year=version.performance_year,
        program=version.program,
        is_program_member=version.is_program_member,
        fields=[
            _field_response(field)
            for field in sorted(version.fields, key=lambda item: item.field.value)
        ],
    )


def _summary(
    session: Session,
    measure: Measure,
    from_year: int | None,
    to_year: int | None,
) -> PublicMeasureSummary:
    versions = _versions_for_measure(session, measure.id)
    comparison = _published_comparison(session, measure.id, from_year, to_year)
    return PublicMeasureSummary(
        measure_id=measure.measure_id,
        name=measure.name,
        description=measure.description,
        performance_years=sorted(
            {version.performance_year for version in versions if version.is_program_member}
        ),
        change_status=comparison.status if comparison else ChangeStatus.UNKNOWN,
        affected_fields=(
            sorted((item.field for item in comparison.affected_fields), key=str)
            if comparison
            else []
        ),
        freshness=_freshness(versions),
    )


def list_performance_years(session: Session) -> list[int]:
    statement = (
        select(ProgramMembership.performance_year)
        .join(Measure)
        .where(
            Measure.is_public.is_(True),
            ProgramMembership.is_program_member.is_(True),
            ProgramMembership.publication_state == PublicationState.PUBLISHED,
        )
        .distinct()
        .order_by(ProgramMembership.performance_year)
    )
    return list(session.scalars(statement))


def list_measures(session: Session, filters: MeasureFilters) -> PublicMeasurePage:
    statement = select(Measure).where(
        Measure.is_public.is_(True),
        Measure.versions.any(MeasureVersion.publication_state == PublicationState.PUBLISHED),
    )
    if filters.q:
        pattern = f"%{filters.q.strip()}%"
        statement = statement.where(
            or_(
                Measure.measure_id.ilike(pattern),
                Measure.name.ilike(pattern),
                Measure.description.ilike(pattern),
            )
        )
    if filters.performance_year is not None:
        statement = statement.where(
            Measure.memberships.any(
                (ProgramMembership.performance_year == filters.performance_year)
                & ProgramMembership.is_program_member.is_(True)
                & (ProgramMembership.publication_state == PublicationState.PUBLISHED)
            )
        )
    if filters.verification_status is not None:
        statement = statement.where(
            Measure.versions.any(
                (MeasureVersion.verification_status == filters.verification_status)
                & (MeasureVersion.publication_state == PublicationState.PUBLISHED)
            )
        )
    if filters.change_status is not None or filters.affected_field is not None:
        comparison_predicates = [MeasureComparison.publication_state == PublicationState.PUBLISHED]
        if filters.from_year is not None:
            comparison_predicates.append(MeasureComparison.from_year == filters.from_year)
        if filters.to_year is not None:
            comparison_predicates.append(MeasureComparison.to_year == filters.to_year)
        if filters.change_status is not None:
            comparison_predicates.append(MeasureComparison.status == filters.change_status)
        if filters.affected_field is not None:
            comparison_predicates.append(
                MeasureComparison.affected_fields.any(
                    MeasureComparisonField.field == filters.affected_field
                )
            )
        statement = statement.where(Measure.comparisons.any(and_(*comparison_predicates)))

    count_statement = select(func.count()).select_from(statement.subquery())
    total_items = session.scalar(count_statement) or 0
    measures = list(
        session.scalars(
            statement.order_by(Measure.measure_id)
            .offset((filters.page - 1) * filters.page_size)
            .limit(filters.page_size)
        )
    )
    items = [_summary(session, measure, filters.from_year, filters.to_year) for measure in measures]
    return PublicMeasurePage(
        items=items,
        pagination=PaginationMeta(
            page=filters.page,
            page_size=filters.page_size,
            total_items=total_items,
            total_pages=math.ceil(total_items / filters.page_size) if total_items else 0,
        ),
    )


def get_measure(
    session: Session,
    measure_id: str,
    from_year: int | None,
    to_year: int | None,
) -> PublicMeasureDetail | None:
    measure = session.scalar(
        select(Measure).where(Measure.measure_id == measure_id, Measure.is_public.is_(True))
    )
    if not measure:
        return None
    selected_years = {year for year in (from_year, to_year) if year is not None}
    versions = _versions_for_measure(session, measure.id, selected_years or None)
    if not versions:
        return None
    summary = _summary(session, measure, from_year, to_year)
    return PublicMeasureDetail(
        **summary.model_dump(),
        versions=[_version_response(version) for version in versions],
    )


def list_measure_versions(
    session: Session,
    measure_id: str,
    performance_year: int | None,
) -> list[MeasureVersionResponse] | None:
    measure = session.scalar(
        select(Measure).where(Measure.measure_id == measure_id, Measure.is_public.is_(True))
    )
    if not measure:
        return None
    years = {performance_year} if performance_year is not None else None
    versions = _versions_for_measure(session, measure.id, years)
    return [_version_response(version) for version in versions]
