from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import IngestionRun, IngestionRunItem
from app.schemas import (
    AdminIngestionEventResponse,
    AdminIngestionItemResponse,
    AdminIngestionRunListResponse,
    AdminIngestionRunResponse,
)


def _query():
    return select(IngestionRun).options(
        selectinload(IngestionRun.items).selectinload(IngestionRunItem.source_document),
        selectinload(IngestionRun.items).selectinload(IngestionRunItem.source_check),
        selectinload(IngestionRun.items).selectinload(IngestionRunItem.events),
    )


def ingestion_run_response(run: IngestionRun) -> AdminIngestionRunResponse:
    return AdminIngestionRunResponse(
        run_id=run.run_id,
        status=run.status,
        source_count=run.source_count,
        completed_count=run.completed_count,
        failed_count=run.failed_count,
        started_at=run.started_at,
        completed_at=run.completed_at,
        created_by=run.created_by,
        items=[
            AdminIngestionItemResponse(
                item_id=item.item_id,
                sequence=item.sequence,
                source_id=item.source_document.source_id,
                source_title=item.source_document.title,
                stage=item.stage,
                source_check_id=(item.source_check.check_id if item.source_check else None),
                source_check_outcome=(item.source_check.outcome if item.source_check else None),
                started_at=item.started_at,
                completed_at=item.completed_at,
                error=item.error,
                events=[
                    AdminIngestionEventResponse(
                        event_id=event.event_id,
                        stage=event.stage,
                        occurred_at=event.occurred_at,
                        detail=event.detail,
                    )
                    for event in sorted(item.events, key=lambda value: value.sequence)
                ],
            )
            for item in sorted(run.items, key=lambda value: value.sequence)
        ],
    )


def get_ingestion_run(session: Session, run_id: str) -> IngestionRun | None:
    return session.scalar(_query().where(IngestionRun.run_id == run_id))


def list_ingestion_runs(session: Session, *, limit: int = 20) -> AdminIngestionRunListResponse:
    runs = list(
        session.scalars(
            _query().order_by(IngestionRun.started_at.desc()).limit(limit)
        ).unique()
    )
    return AdminIngestionRunListResponse(
        items=[ingestion_run_response(run) for run in runs]
    )
