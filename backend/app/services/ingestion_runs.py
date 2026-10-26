from datetime import UTC, datetime
from uuid import uuid4

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.domain import (
    IngestionItemStage,
    IngestionRunStatus,
    SourceCheckOutcome,
    SourceExtractionStatus,
)
from app.models import (
    IngestionRun,
    IngestionRunEvent,
    IngestionRunItem,
    SourceDocument,
)
from app.services.source_ingestion import SourceFetchError, fetch_registered_source
from app.services.source_normalization import SourceNormalizationError, normalize_extraction


class IngestionRunError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _now() -> datetime:
    return datetime.now(UTC)


def _event(
    session: Session,
    item: IngestionRunItem,
    stage: IngestionItemStage,
    detail: str | None = None,
) -> None:
    sequence = (
        session.scalar(
            select(func.max(IngestionRunEvent.sequence)).where(
                IngestionRunEvent.ingestion_run_item_id == item.id
            )
        )
        or 0
    ) + 1
    item.stage = stage
    item.events.append(
        IngestionRunEvent(
            event_id=f"{item.item_id}-E{sequence}",
            sequence=sequence,
            stage=stage,
            detail=detail,
        )
    )
    session.flush()


def create_ingestion_run(
    session: Session,
    *,
    created_by: str,
    max_sources: int,
) -> IngestionRun:
    if max_sources < 1:
        raise IngestionRunError(
            "ingestion_limit_invalid", "The ingestion source limit must be at least one."
        )

    active_run = session.scalar(
        select(IngestionRun).where(IngestionRun.status == IngestionRunStatus.RUNNING)
    )
    if active_run is not None:
        raise IngestionRunError(
            "ingestion_run_already_running",
            f"Ingestion run '{active_run.run_id}' is still active.",
        )

    sources = list(
        session.scalars(
            select(SourceDocument)
            .where(SourceDocument.is_active.is_(True))
            .order_by(SourceDocument.source_id)
        )
    )
    if len(sources) > max_sources:
        raise IngestionRunError(
            "ingestion_source_limit_exceeded",
            f"{len(sources)} active sources exceed the configured run limit of {max_sources}.",
        )

    run_key = uuid4().hex
    run = IngestionRun(
        run_id=f"CMS-INGEST-{run_key}",
        status=IngestionRunStatus.RUNNING,
        source_count=len(sources),
        completed_count=0,
        failed_count=0,
        created_by=created_by,
        items=[
            IngestionRunItem(
                item_id=f"CMS-INGEST-ITEM-{run_key}-{index}",
                sequence=index,
                stage=IngestionItemStage.PENDING,
                source_document=source,
            )
            for index, source in enumerate(sources, start=1)
        ],
    )
    session.add(run)
    session.flush()
    for item in run.items:
        _event(session, item, IngestionItemStage.PENDING, "Queued for source retrieval.")
    return run


def execute_ingestion_run(
    session: Session,
    run: IngestionRun,
    *,
    settings: Settings,
    checked_by: str,
    client: httpx.Client | None = None,
) -> IngestionRun:
    if run.status != IngestionRunStatus.RUNNING:
        raise IngestionRunError(
            "ingestion_run_not_running", "Only a running ingestion run can be executed."
        )

    # The run and its pending items are durable before the first network operation.
    session.commit()
    owns_client = client is None
    http_client = client or httpx.Client(timeout=settings.source_fetch_timeout_seconds)
    try:
        for item in sorted(run.items, key=lambda value: value.sequence):
            item.started_at = _now()
            _event(session, item, IngestionItemStage.DOWNLOADING, "Retrieving official CMS source.")
            session.commit()
            try:
                def extraction_started(run_item: IngestionRunItem = item) -> None:
                    _event(
                        session,
                        run_item,
                        IngestionItemStage.EXTRACTING,
                        "Extracting traceable text from the changed source revision.",
                    )
                    session.commit()

                check = fetch_registered_source(
                    session,
                    item.source_document,
                    settings=settings,
                    checked_by=checked_by,
                    force=False,
                    client=http_client,
                    on_extraction_started=extraction_started,
                )
                item.source_check = check

                if check.outcome == SourceCheckOutcome.UNCHANGED:
                    _event(
                        session,
                        item,
                        IngestionItemStage.COMPARING,
                        "Content hash compared with stored revisions.",
                    )
                    final_stage = IngestionItemStage.UNCHANGED
                    detail = "The retrieved content matches an existing immutable revision."
                elif check.extraction is None:
                    final_stage = IngestionItemStage.FAILED
                    detail = "The source check did not produce an extraction."
                elif check.extraction.status == SourceExtractionStatus.FAILED:
                    final_stage = IngestionItemStage.FAILED
                    detail = check.extraction.error or "Text extraction failed."
                elif check.extraction.status == SourceExtractionStatus.MANUAL_REVIEW:
                    final_stage = IngestionItemStage.AWAITING_VERIFICATION
                    detail = check.extraction.error or "Manual source review is required."
                else:
                    try:
                        _event(
                            session,
                            item,
                            IngestionItemStage.COMPARING,
                            "Matching extracted identity and fields to private stored versions.",
                        )
                        normalization = normalize_extraction(
                            session, check.extraction, created_by=checked_by
                        )
                        detail = (
                            "Private normalized candidates are ready for verification "
                            f"({normalization.status.value})."
                        )
                        final_stage = IngestionItemStage.AWAITING_VERIFICATION
                    except SourceNormalizationError as error:
                        final_stage = IngestionItemStage.FAILED
                        detail = error.message

                if final_stage == IngestionItemStage.FAILED:
                    item.error = detail
                    run.failed_count += 1
                item.completed_at = _now()
                _event(session, item, final_stage, detail)
            except SourceFetchError as error:
                item.source_check = error.check
                item.error = error.message
                item.completed_at = _now()
                run.failed_count += 1
                _event(session, item, IngestionItemStage.FAILED, error.message)
            run.completed_count += 1
            session.commit()

        run.status = (
            IngestionRunStatus.COMPLETED_WITH_ERRORS
            if run.failed_count
            else IngestionRunStatus.COMPLETED
        )
        run.completed_at = _now()
        session.commit()
        return run
    finally:
        if owns_client:
            http_client.close()
