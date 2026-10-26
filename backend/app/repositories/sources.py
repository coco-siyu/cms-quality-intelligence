from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import SourceCheck, SourceDocument, SourceExtraction, SourceRevision
from app.schemas import (
    AdminSourceCheckResponse,
    AdminSourceDetailResponse,
    AdminSourceExtractionDetailResponse,
    AdminSourceExtractionResponse,
    AdminSourceListResponse,
    AdminSourceRevisionResponse,
    AdminSourceSegmentResponse,
    AdminSourceSummaryResponse,
)


def source_format(mime_type: str) -> str:
    return "pdf" if mime_type == "application/pdf" else "html"


def _extraction_response(
    extraction: SourceExtraction | None,
) -> AdminSourceExtractionResponse | None:
    if extraction is None:
        return None
    return AdminSourceExtractionResponse(
        extraction_id=extraction.extraction_id,
        sequence=extraction.sequence,
        status=extraction.status,
        page_count=extraction.page_count,
        segment_count=len(extraction.segments),
        error=extraction.error,
        extractor_version=extraction.extractor_version,
        forced=extraction.forced,
        extracted_at=extraction.extracted_at,
        created_by=extraction.created_by,
    )


def _revision_response(revision: SourceRevision) -> AdminSourceRevisionResponse:
    latest_extraction = max(revision.extractions, key=lambda item: item.sequence, default=None)
    return AdminSourceRevisionResponse(
        revision_id=revision.revision_id,
        revision_number=revision.revision_number,
        content_hash=revision.content_hash,
        source_url=revision.source_url,
        final_url=revision.final_url,
        http_status=revision.http_status,
        mime_type=revision.retrieved_mime_type,
        byte_length=revision.byte_length,
        publication_date=revision.publication_date,
        retrieved_at=revision.retrieved_at,
        last_source_check_at=revision.last_source_check_at,
        extraction=_extraction_response(latest_extraction),
    )


def _check_response(check: SourceCheck) -> AdminSourceCheckResponse:
    return AdminSourceCheckResponse(
        check_id=check.check_id,
        outcome=check.outcome,
        checked_at=check.checked_at,
        requested_url=check.requested_url,
        final_url=check.final_url,
        http_status=check.http_status,
        mime_type=check.mime_type,
        byte_length=check.byte_length,
        content_hash=check.content_hash,
        error=check.error,
        forced=check.forced,
        checked_by=check.checked_by,
        revision_id=check.source_revision.revision_id if check.source_revision else None,
        extraction_id=check.extraction.extraction_id if check.extraction else None,
    )


def _source_query():
    return select(SourceDocument).options(
        selectinload(SourceDocument.revisions)
        .selectinload(SourceRevision.extractions)
        .selectinload(SourceExtraction.segments),
        selectinload(SourceDocument.checks).selectinload(SourceCheck.source_revision),
        selectinload(SourceDocument.checks).selectinload(SourceCheck.extraction),
    )


def _summary(source: SourceDocument) -> AdminSourceSummaryResponse:
    latest_revision = max(
        source.revisions, key=lambda item: item.revision_number, default=None
    )
    latest_check = max(source.checks, key=lambda item: item.checked_at, default=None)
    return AdminSourceSummaryResponse(
        source_id=source.source_id,
        title=source.title,
        official_url=source.official_url,
        source_format=source_format(source.mime_type),
        is_active=source.is_active,
        notes=source.notes,
        created_by=source.created_by,
        created_at=source.created_at,
        updated_at=source.updated_at,
        deactivated_at=source.deactivated_at,
        revision_count=len(source.revisions),
        latest_revision=_revision_response(latest_revision) if latest_revision else None,
        latest_check=_check_response(latest_check) if latest_check else None,
    )


def list_sources(session: Session) -> AdminSourceListResponse:
    sources = list(session.scalars(_source_query().order_by(SourceDocument.source_id)).unique())
    return AdminSourceListResponse(items=[_summary(source) for source in sources])


def get_source_model(session: Session, source_id: str) -> SourceDocument | None:
    return session.scalar(
        _source_query().where(SourceDocument.source_id == source_id)
    )


def source_detail(source: SourceDocument) -> AdminSourceDetailResponse:
    summary = _summary(source)
    return AdminSourceDetailResponse(
        **summary.model_dump(),
        revisions=[
            _revision_response(revision)
            for revision in sorted(
                source.revisions, key=lambda item: item.revision_number, reverse=True
            )
        ],
        checks=[
            _check_response(check)
            for check in sorted(source.checks, key=lambda item: item.checked_at, reverse=True)
        ],
    )


def get_extraction_detail(
    session: Session, extraction_id: str
) -> AdminSourceExtractionDetailResponse | None:
    extraction = session.scalar(
        select(SourceExtraction)
        .where(SourceExtraction.extraction_id == extraction_id)
        .options(
            selectinload(SourceExtraction.segments),
            selectinload(SourceExtraction.source_revision).selectinload(
                SourceRevision.source_document
            ),
        )
    )
    if extraction is None:
        return None
    summary = _extraction_response(extraction)
    if summary is None:  # pragma: no cover - narrowed by the query above
        return None
    return AdminSourceExtractionDetailResponse(
        **summary.model_dump(),
        source_id=extraction.source_revision.source_document.source_id,
        revision_id=extraction.source_revision.revision_id,
        segments=[
            AdminSourceSegmentResponse(
                sequence=segment.sequence,
                locator=segment.locator,
                text=segment.text,
            )
            for segment in sorted(extraction.segments, key=lambda item: item.sequence)
        ],
    )
