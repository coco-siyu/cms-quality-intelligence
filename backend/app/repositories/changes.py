import math
from dataclasses import dataclass

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from app.domain import (
    AffectedField,
    ChangeStatus,
    CollectionType,
    ComparisonEvidenceStatus,
    PublicationState,
)
from app.models import (
    EvidenceReference,
    Measure,
    MeasureComparison,
    MeasureComparisonEvidence,
    MeasureComparisonField,
    SourceRevision,
    SpecificationField,
)
from app.schemas import PaginationMeta, PublicChangePage, PublicChangeRecord
from app.services.comparison_evidence import build_public_change_record

CHANGED_FIELD_STATUSES = (
    ChangeStatus.ADDED,
    ChangeStatus.REMOVED,
    ChangeStatus.MODIFIED,
    ChangeStatus.WORDING_ONLY,
)


@dataclass(frozen=True)
class ChangeFilters:
    from_year: int | None = None
    to_year: int | None = None
    change_status: ChangeStatus | None = None
    affected_field: AffectedField | None = None
    collection_type: CollectionType | None = None
    page: int = 1
    page_size: int = 25


def _public_change_statement() -> Select[tuple[MeasureComparison]]:
    links = selectinload(MeasureComparison.affected_fields).selectinload(
        MeasureComparisonField.evidence_links
    )
    references = links.selectinload(MeasureComparisonEvidence.evidence_reference)
    return (
        select(MeasureComparison)
        .join(MeasureComparison.measure)
        .where(
            Measure.is_public.is_(True),
            MeasureComparison.publication_state == PublicationState.PUBLISHED,
            MeasureComparison.evidence_status == ComparisonEvidenceStatus.VERIFIED,
        )
        .options(
            selectinload(MeasureComparison.measure),
            references.selectinload(EvidenceReference.source_revision).selectinload(
                SourceRevision.source_document
            ),
            references.selectinload(EvidenceReference.specification_field).selectinload(
                SpecificationField.measure_version
            ),
        )
    )


def _filtered_statement(filters: ChangeFilters) -> Select[tuple[MeasureComparison]]:
    statement = _public_change_statement()
    if filters.from_year is not None:
        statement = statement.where(MeasureComparison.from_year == filters.from_year)
    if filters.to_year is not None:
        statement = statement.where(MeasureComparison.to_year == filters.to_year)
    if filters.change_status is not None:
        statement = statement.where(MeasureComparison.status == filters.change_status)
    if filters.affected_field is not None:
        statement = statement.where(
            MeasureComparison.affected_fields.any(
                (MeasureComparisonField.field == filters.affected_field)
                & (MeasureComparisonField.status.in_(CHANGED_FIELD_STATUSES))
            )
        )
    if filters.collection_type is not None:
        statement = statement.where(MeasureComparison.collection_type == filters.collection_type)
    return statement


def _project_public_changes(
    session: Session,
    statement: Select[tuple[MeasureComparison]],
) -> list[PublicChangeRecord]:
    comparisons = session.scalars(
        statement.order_by(
            MeasureComparison.published_at.desc(),
            Measure.measure_id,
            MeasureComparison.from_year,
            MeasureComparison.to_year,
            MeasureComparison.collection_type,
            MeasureComparison.program,
        )
    ).unique()
    return [
        record
        for comparison in comparisons
        if (record := build_public_change_record(comparison)) is not None
    ]


def list_public_changes(session: Session, filters: ChangeFilters) -> PublicChangePage:
    records = _project_public_changes(session, _filtered_statement(filters))
    total_items = len(records)
    start = (filters.page - 1) * filters.page_size
    return PublicChangePage(
        items=records[start : start + filters.page_size],
        pagination=PaginationMeta(
            page=filters.page,
            page_size=filters.page_size,
            total_items=total_items,
            total_pages=math.ceil(total_items / filters.page_size) if total_items else 0,
        ),
    )


def get_public_change(
    session: Session,
    *,
    measure_id: str,
    program: str,
    collection_type: CollectionType,
    from_year: int,
    to_year: int,
) -> PublicChangeRecord | None:
    statement = _public_change_statement().where(
        Measure.measure_id == measure_id,
        MeasureComparison.program == program,
        MeasureComparison.collection_type == collection_type,
        MeasureComparison.from_year == from_year,
        MeasureComparison.to_year == to_year,
    )
    records = _project_public_changes(session, statement)
    return records[0] if records else None
