from collections.abc import Callable

import httpx
import pytest
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.domain import SourceCheckOutcome, SourceExtractionStatus
from app.models import SourceCheck, SourceDocument, SourceExtraction, SourceRevision
from app.services.source_ingestion import (
    SourceFetchError,
    extract_pdf,
    fetch_registered_source,
)
from app.services.source_registry import SourceRegistryError, validate_official_cms_url


def _source(session: Session, *, source_format: str = "html") -> SourceDocument:
    source = SourceDocument(
        source_id=f"CMS-TEST-{source_format.upper()}",
        title=f"CMS {source_format.upper()} source test",
        official_url=f"https://www.cms.gov/test/source.{source_format}",
        mime_type="application/pdf" if source_format == "pdf" else "text/html",
        created_by="reviewer",
    )
    session.add(source)
    session.flush()
    return source


def _client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def _text_pdf(text: str) -> bytes:
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode())
        output.extend(body)
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode()
    )
    return bytes(output)


@pytest.mark.parametrize(
    "url",
    [
        "http://www.cms.gov/source",
        "https://example.com/source",
        "https://cms.gov.example.com/source",
        "https://127.0.0.1/source",
        "https://user:password@cms.gov/source",
        "https://cms.gov:8443/source",
        "https://cms.gov/source#section",
    ],
)
def test_source_registry_rejects_unsafe_or_non_cms_urls(url: str) -> None:
    with pytest.raises(SourceRegistryError):
        validate_official_cms_url(url)


def test_source_registry_accepts_cms_hosts() -> None:
    assert validate_official_cms_url("https://www.cms.gov/source") == (
        "https://www.cms.gov/source"
    )
    assert validate_official_cms_url("https://cms.gov/source") == "https://cms.gov/source"


def test_html_checks_preserve_revisions_and_forced_extraction_history(
    session: Session,
) -> None:
    source = _source(session)
    settings = Settings(source_fetch_max_bytes=10_000)
    content = b"<html><h1>Quality requirements</h1><p>Official CMS text.</p></html>"

    def respond(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "text/html"}, content=content)

    with _client(respond) as client:
        first = fetch_registered_source(
            session,
            source,
            settings=settings,
            checked_by="reviewer",
            force=False,
            client=client,
        )
        unchanged = fetch_registered_source(
            session,
            source,
            settings=settings,
            checked_by="reviewer",
            force=False,
            client=client,
        )
        forced = fetch_registered_source(
            session,
            source,
            settings=settings,
            checked_by="reviewer",
            force=True,
            client=client,
        )
    session.commit()

    assert first.outcome == SourceCheckOutcome.NEW_REVISION
    assert unchanged.outcome == SourceCheckOutcome.UNCHANGED
    assert unchanged.extraction is None
    assert forced.outcome == SourceCheckOutcome.REPROCESSED
    assert session.query(SourceRevision).count() == 1
    assert session.query(SourceExtraction).count() == 2
    assert forced.extraction is not None
    assert [segment.locator for segment in forced.extraction.segments] == [
        "HTML heading: Quality requirements",
        "HTML section: Quality requirements",
    ]


def test_changed_content_creates_a_new_immutable_revision(session: Session) -> None:
    source = _source(session)
    settings = Settings(source_fetch_max_bytes=10_000)
    bodies = iter(
        [
            b"<html><p>First official version.</p></html>",
            b"<html><p>Second official version.</p></html>",
        ]
    )

    def respond(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, headers={"content-type": "text/html"}, content=next(bodies)
        )

    with _client(respond) as client:
        fetch_registered_source(
            session,
            source,
            settings=settings,
            checked_by="reviewer",
            force=False,
            client=client,
        )
        fetch_registered_source(
            session,
            source,
            settings=settings,
            checked_by="reviewer",
            force=False,
            client=client,
        )
    session.commit()

    revisions = list(
        session.scalars(select(SourceRevision).order_by(SourceRevision.revision_number))
    )
    assert [revision.revision_number for revision in revisions] == [1, 2]
    assert revisions[0].content_blob == b"<html><p>First official version.</p></html>"
    assert revisions[1].content_blob == b"<html><p>Second official version.</p></html>"
    assert revisions[0].content_hash != revisions[1].content_hash


def test_redirects_are_revalidated_before_following(session: Session) -> None:
    source = _source(session)

    def redirect(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "https://example.com/private"})

    with _client(redirect) as client, pytest.raises(SourceFetchError):
        fetch_registered_source(
            session,
            source,
            settings=Settings(),
            checked_by="reviewer",
            force=False,
            client=client,
        )
    session.commit()

    check = session.scalar(select(SourceCheck))
    assert check is not None
    assert check.outcome == SourceCheckOutcome.FAILED
    assert "cms.gov" in (check.error or "")
    assert session.query(SourceRevision).count() == 0


def test_pdf_text_is_extracted_with_page_locators(session: Session) -> None:
    content = _text_pdf("CMS quality measure source text")
    assert len(PdfReader(__import__("io").BytesIO(content)).pages) == 1
    result = extract_pdf(content)

    assert result.status == SourceExtractionStatus.EXTRACTED
    assert result.page_count == 1
    assert result.segments[0].locator == "PDF page 1"
    assert result.segments[0].text == "CMS quality measure source text"


def test_pdf_without_machine_readable_text_requires_manual_review() -> None:
    from io import BytesIO

    from pypdf import PdfWriter

    output = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.write(output)

    result = extract_pdf(output.getvalue())

    assert result.status == SourceExtractionStatus.MANUAL_REVIEW
    assert result.page_count == 1
    assert result.segments == ()


def test_source_download_limit_is_enforced_and_audited(session: Session) -> None:
    source = _source(session)

    def oversized(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/html", "content-length": "1000"},
            content=b"<html><p>Too large.</p></html>",
        )

    with _client(oversized) as client, pytest.raises(SourceFetchError):
        fetch_registered_source(
            session,
            source,
            settings=Settings(source_fetch_max_bytes=100),
            checked_by="reviewer",
            force=False,
            client=client,
        )
    session.commit()

    check = session.scalar(select(SourceCheck))
    assert check is not None
    assert check.outcome == SourceCheckOutcome.FAILED
    assert "download limit" in (check.error or "")
