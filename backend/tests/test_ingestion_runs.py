import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.domain import IngestionItemStage, IngestionRunStatus
from app.models import IngestionRun, SourceCheck, SourceDocument
from app.services.ingestion_runs import (
    IngestionRunError,
    create_ingestion_run,
    execute_ingestion_run,
    execute_ingestion_run_by_id,
)


def _source(source_id: str, path: str) -> SourceDocument:
    return SourceDocument(
        source_id=source_id,
        title=f"Official test source {source_id}",
        official_url=f"https://www.cms.gov/{path}",
        mime_type="text/html",
        created_by="reviewer",
    )


def _html(title: str) -> bytes:
    return (
        "<!doctype html><html><body>"
        f"<h1>Measure Title</h1><p>{title}</p>"
        "<h2>Description</h2><p>Official source wording for a test candidate.</p>"
        "</body></html>"
    ).encode()


def test_ingestion_run_persists_stage_history_and_private_candidates(
    session: Session,
) -> None:
    session.add_all([_source("CMS-A", "source-a"), _source("CMS-B", "source-b")])
    session.commit()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            content=_html(request.url.path),
        )

    run = create_ingestion_run(session, created_by="reviewer", max_sources=5)
    execute_ingestion_run(
        session,
        run,
        settings=Settings(),
        checked_by="reviewer",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert run.status == IngestionRunStatus.COMPLETED
    assert run.completed_count == 2
    assert run.failed_count == 0
    assert all(item.stage == IngestionItemStage.AWAITING_VERIFICATION for item in run.items)
    assert [event.stage for event in run.items[0].events] == [
        IngestionItemStage.PENDING,
        IngestionItemStage.DOWNLOADING,
        IngestionItemStage.EXTRACTING,
        IngestionItemStage.COMPARING,
        IngestionItemStage.AWAITING_VERIFICATION,
    ]
    assert all(item.source_check is not None for item in run.items)
    assert all(
        item.source_check.extraction.normalizations
        for item in run.items
        if item.source_check and item.source_check.extraction
    )
    assert session.scalar(select(IngestionRun).where(IngestionRun.run_id == run.run_id))

    unchanged_run = create_ingestion_run(
        session, created_by="reviewer", max_sources=5
    )
    execute_ingestion_run(
        session,
        unchanged_run,
        settings=Settings(),
        checked_by="reviewer",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    assert all(item.stage == IngestionItemStage.UNCHANGED for item in unchanged_run.items)
    assert [event.stage for event in unchanged_run.items[0].events] == [
        IngestionItemStage.PENDING,
        IngestionItemStage.DOWNLOADING,
        IngestionItemStage.COMPARING,
        IngestionItemStage.UNCHANGED,
    ]


def test_ingestion_run_continues_after_one_source_fails(session: Session) -> None:
    session.add_all([_source("CMS-FAIL", "fail"), _source("CMS-OK", "ok")])
    session.commit()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/fail":
            return httpx.Response(503, content=b"unavailable")
        return httpx.Response(
            200, headers={"content-type": "text/html"}, content=_html("Working")
        )

    run = create_ingestion_run(
        session, created_by="reviewer", max_sources=5, max_attempts=2
    )
    execute_ingestion_run(
        session,
        run,
        settings=Settings(ingestion_retry_backoff_seconds=0),
        checked_by="reviewer",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert run.status == IngestionRunStatus.COMPLETED_WITH_ERRORS
    assert run.completed_count == 2
    assert run.failed_count == 1
    assert {item.stage for item in run.items} == {
        IngestionItemStage.FAILED,
        IngestionItemStage.AWAITING_VERIFICATION,
    }
    failed_item = next(item for item in run.items if item.stage == IngestionItemStage.FAILED)
    assert failed_item.attempt_count == 2
    assert failed_item.max_attempts == 2
    assert failed_item.retry_exhausted is True
    assert failed_item.requires_attention is True
    assert "Automatic retries exhausted" in (failed_item.events[-1].detail or "")


def test_ingestion_run_recovers_from_bounded_transient_failures(
    session: Session,
) -> None:
    session.add(_source("CMS-RETRY", "retry"))
    session.commit()
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls < 3:
            return httpx.Response(503, content=b"temporarily unavailable")
        return httpx.Response(
            200, headers={"content-type": "text/html"}, content=_html("Recovered")
        )

    run = create_ingestion_run(
        session, created_by="reviewer", max_sources=5, max_attempts=3
    )
    execute_ingestion_run(
        session,
        run,
        settings=Settings(ingestion_retry_backoff_seconds=0),
        checked_by="reviewer",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    item = run.items[0]
    assert calls == 3
    assert run.status == IngestionRunStatus.COMPLETED
    assert item.stage == IngestionItemStage.AWAITING_VERIFICATION
    assert item.attempt_count == 3
    assert item.retry_exhausted is False
    assert item.requires_attention is False
    assert session.query(SourceCheck).count() == 3
    assert sum("Retrying automatically" in (event.detail or "") for event in item.events) == 2


def test_ingestion_run_does_not_retry_permanent_content_failure(
    session: Session,
) -> None:
    session.add(_source("CMS-PERMANENT", "permanent"))
    session.commit()
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200, headers={"content-type": "text/plain"}, content=b"not html"
        )

    run = create_ingestion_run(
        session, created_by="reviewer", max_sources=5, max_attempts=3
    )
    execute_ingestion_run(
        session,
        run,
        settings=Settings(ingestion_retry_backoff_seconds=0),
        checked_by="reviewer",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    item = run.items[0]
    assert calls == 1
    assert run.status == IngestionRunStatus.COMPLETED_WITH_ERRORS
    assert item.stage == IngestionItemStage.FAILED
    assert item.attempt_count == 1
    assert item.retry_exhausted is False
    assert item.requires_attention is True
    assert "Permanent retrieval failure" in (item.events[-1].detail or "")


def test_background_run_persists_an_unexpected_interruption(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    session.add(_source("CMS-INTERRUPTED", "interrupted"))
    session.commit()
    run = create_ingestion_run(session, created_by="reviewer", max_sources=5)
    run.items[0].stage = IngestionItemStage.DOWNLOADING
    session.commit()

    factory = sessionmaker(bind=session.get_bind(), expire_on_commit=False)
    monkeypatch.setattr("app.services.ingestion_runs.SessionLocal", factory)

    def fail_unexpectedly(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("parser process exited")

    monkeypatch.setattr(
        "app.services.ingestion_runs.execute_ingestion_run", fail_unexpectedly
    )
    execute_ingestion_run_by_id(
        run.run_id,
        settings=Settings(),
        checked_by="reviewer",
    )

    session.expire_all()
    interrupted = session.scalar(
        select(IngestionRun).where(IngestionRun.run_id == run.run_id)
    )
    assert interrupted is not None
    assert interrupted.status == IngestionRunStatus.INTERRUPTED
    assert interrupted.completed_at is not None
    assert interrupted.completed_count == 1
    assert interrupted.failed_count == 1
    assert interrupted.items[0].stage == IngestionItemStage.FAILED
    assert interrupted.items[0].error == (
        "Ingestion stopped unexpectedly: parser process exited"
    )
    assert interrupted.items[0].events[-1].stage == IngestionItemStage.FAILED


def test_new_run_is_rejected_while_another_run_is_active(session: Session) -> None:
    session.add(_source("CMS-ONE", "one"))
    session.commit()
    stale = create_ingestion_run(session, created_by="reviewer", max_sources=5)
    session.commit()

    with pytest.raises(IngestionRunError, match="still active") as error:
        create_ingestion_run(session, created_by="reviewer", max_sources=5)

    assert error.value.code == "ingestion_run_already_running"
    assert stale.status == IngestionRunStatus.RUNNING
    assert stale.completed_at is None


def test_ingestion_run_rejects_an_unbounded_registry(session: Session) -> None:
    session.add_all([_source("CMS-A", "a"), _source("CMS-B", "b")])
    session.commit()

    with pytest.raises(IngestionRunError, match="configured run limit") as error:
        create_ingestion_run(session, created_by="reviewer", max_sources=1)

    assert error.value.code == "ingestion_source_limit_exceeded"
    assert session.scalars(select(IngestionRun)).all() == []


@pytest.mark.parametrize("max_attempts", [0, 6])
def test_ingestion_run_rejects_an_unsafe_attempt_limit(
    session: Session, max_attempts: int
) -> None:
    with pytest.raises(IngestionRunError, match="between one and five") as error:
        create_ingestion_run(
            session,
            created_by="reviewer",
            max_sources=1,
            max_attempts=max_attempts,
        )

    assert error.value.code == "ingestion_attempt_limit_invalid"
