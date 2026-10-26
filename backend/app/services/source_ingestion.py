import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from io import BytesIO
from urllib.parse import urljoin
from uuid import uuid4

import httpx
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.domain import (
    PublicationState,
    PublicVerificationStatus,
    SourceCheckOutcome,
    SourceExtractionStatus,
)
from app.models import (
    SourceCheck,
    SourceDocument,
    SourceExtraction,
    SourceRevision,
    SourceTextSegment,
)
from app.services.source_registry import SourceRegistryError, validate_official_cms_url

USER_AGENT = "CMS-Quality-Intelligence-source-ingestion/0.1"
HTML_EXTRACTOR_VERSION = "stdlib-html-v1"
PDF_EXTRACTOR_VERSION = "pypdf-v1"
REDIRECT_STATUSES = {301, 302, 303, 307, 308}


class SourceFetchError(RuntimeError):
    def __init__(self, code: str, message: str, check: SourceCheck) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.check = check


@dataclass(frozen=True)
class RetrievedSource:
    final_url: str
    http_status: int
    mime_type: str
    content: bytes


@dataclass(frozen=True)
class ExtractedSegment:
    locator: str
    text: str


@dataclass(frozen=True)
class ExtractionResult:
    status: SourceExtractionStatus
    segments: tuple[ExtractedSegment, ...]
    page_count: int | None
    error: str | None
    extractor_version: str


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


class _ReadableHTMLParser(HTMLParser):
    block_tags = {"p", "li", "td", "th", "h1", "h2", "h3", "h4", "h5", "h6"}
    skipped_tags = {"script", "style", "noscript", "svg"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.current_heading = "Document body"
        self.active_tag: str | None = None
        self.buffer: list[str] = []
        self.skip_depth = 0
        self.segments: list[ExtractedSegment] = []

    def handle_starttag(self, tag: str, _attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in self.skipped_tags:
            self.skip_depth += 1
            return
        if self.skip_depth == 0 and tag in self.block_tags and self.active_tag is None:
            self.active_tag = tag
            self.buffer = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self.skipped_tags and self.skip_depth:
            self.skip_depth -= 1
            return
        if self.skip_depth or self.active_tag != tag:
            return
        text = _normalize_text(" ".join(self.buffer))
        if text:
            if tag.startswith("h"):
                self.current_heading = text
                locator = f"HTML heading: {text}"
            else:
                locator = f"HTML section: {self.current_heading}"
            self.segments.append(ExtractedSegment(locator=locator, text=text))
        self.active_tag = None
        self.buffer = []

    def handle_data(self, data: str) -> None:
        if self.skip_depth == 0 and self.active_tag is not None:
            self.buffer.append(data)


def extract_html(content: bytes, mime_type: str) -> ExtractionResult:
    charset = "utf-8"
    match = re.search(r"charset=([\w-]+)", mime_type, flags=re.IGNORECASE)
    if match:
        charset = match.group(1)
    try:
        text = content.decode(charset, errors="replace")
        parser = _ReadableHTMLParser()
        parser.feed(text)
        parser.close()
    except (LookupError, UnicodeError, ValueError) as error:
        return ExtractionResult(
            status=SourceExtractionStatus.FAILED,
            segments=(),
            page_count=None,
            error=f"HTML extraction failed: {error}",
            extractor_version=HTML_EXTRACTOR_VERSION,
        )
    segments = tuple(parser.segments)
    if not segments:
        return ExtractionResult(
            status=SourceExtractionStatus.MANUAL_REVIEW,
            segments=(),
            page_count=None,
            error="No readable HTML text blocks were found.",
            extractor_version=HTML_EXTRACTOR_VERSION,
        )
    return ExtractionResult(
        status=SourceExtractionStatus.EXTRACTED,
        segments=segments,
        page_count=None,
        error=None,
        extractor_version=HTML_EXTRACTOR_VERSION,
    )


def extract_pdf(content: bytes) -> ExtractionResult:
    try:
        reader = PdfReader(BytesIO(content))
        segments = []
        for page_number, page in enumerate(reader.pages, start=1):
            text = _normalize_text(page.extract_text() or "")
            if text:
                segments.append(
                    ExtractedSegment(locator=f"PDF page {page_number}", text=text)
                )
    except (PdfReadError, OSError, ValueError, TypeError) as error:
        return ExtractionResult(
            status=SourceExtractionStatus.FAILED,
            segments=(),
            page_count=None,
            error=f"PDF extraction failed: {error}",
            extractor_version=PDF_EXTRACTOR_VERSION,
        )
    if not segments:
        return ExtractionResult(
            status=SourceExtractionStatus.MANUAL_REVIEW,
            segments=(),
            page_count=len(reader.pages),
            error="No machine-readable PDF text was found; OCR or manual review is required.",
            extractor_version=PDF_EXTRACTOR_VERSION,
        )
    return ExtractionResult(
        status=SourceExtractionStatus.EXTRACTED,
        segments=tuple(segments),
        page_count=len(reader.pages),
        error=None,
        extractor_version=PDF_EXTRACTOR_VERSION,
    )


def _read_response(response: httpx.Response, max_bytes: int) -> bytes:
    declared_length = response.headers.get("content-length")
    if declared_length:
        try:
            if int(declared_length) > max_bytes:
                raise ValueError("The CMS source exceeds the configured download limit.")
        except ValueError as error:
            if "exceeds" in str(error):
                raise
    chunks: list[bytes] = []
    byte_length = 0
    for chunk in response.iter_bytes():
        byte_length += len(chunk)
        if byte_length > max_bytes:
            raise ValueError("The CMS source exceeds the configured download limit.")
        chunks.append(chunk)
    return b"".join(chunks)


def retrieve_source(
    client: httpx.Client,
    url: str,
    *,
    max_bytes: int,
    max_redirects: int,
) -> RetrievedSource:
    current_url = validate_official_cms_url(url)
    for redirect_count in range(max_redirects + 1):
        with client.stream(
            "GET",
            current_url,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/pdf"},
        ) as response:
            if response.status_code in REDIRECT_STATUSES:
                location = response.headers.get("location")
                if not location:
                    raise ValueError("CMS returned a redirect without a Location header.")
                if redirect_count >= max_redirects:
                    raise ValueError("CMS source exceeded the redirect limit.")
                current_url = validate_official_cms_url(urljoin(current_url, location))
                continue
            response.raise_for_status()
            content = _read_response(response, max_bytes)
            mime_type = response.headers.get("content-type", "").strip().lower()
            return RetrievedSource(
                final_url=current_url,
                http_status=response.status_code,
                mime_type=mime_type,
                content=content,
            )
    raise ValueError("CMS source exceeded the redirect limit.")


def _content_kind(content: bytes, mime_type: str) -> str | None:
    declared = mime_type.split(";", maxsplit=1)[0].strip()
    if content.startswith(b"%PDF-"):
        return "pdf"
    prefix = content[:1024].lstrip().lower()
    if declared in {"text/html", "application/xhtml+xml"} or prefix.startswith(
        (b"<!doctype html", b"<html")
    ):
        return "html"
    return None


def _record_failed_check(
    session: Session,
    source: SourceDocument,
    *,
    checked_by: str,
    forced: bool,
    message: str,
) -> SourceCheck:
    check = SourceCheck(
        check_id=f"CMS-CHECK-{uuid4().hex}",
        source_document=source,
        outcome=SourceCheckOutcome.FAILED,
        requested_url=source.official_url,
        error=message,
        forced=forced,
        checked_by=checked_by,
    )
    session.add(check)
    session.flush()
    return check


def _create_extraction(
    session: Session,
    revision: SourceRevision,
    result: ExtractionResult,
    *,
    forced: bool,
    checked_by: str,
) -> SourceExtraction:
    sequence = (
        session.scalar(
            select(func.max(SourceExtraction.sequence)).where(
                SourceExtraction.source_revision_id == revision.id
            )
        )
        or 0
    ) + 1
    extraction = SourceExtraction(
        extraction_id=f"{revision.revision_id}-X{sequence}",
        source_revision=revision,
        sequence=sequence,
        status=result.status,
        page_count=result.page_count,
        error=result.error,
        extractor_version=result.extractor_version,
        forced=forced,
        created_by=checked_by,
        segments=[
            SourceTextSegment(sequence=index, locator=item.locator, text=item.text)
            for index, item in enumerate(result.segments, start=1)
        ],
    )
    session.add(extraction)
    session.flush()
    return extraction


def fetch_registered_source(
    session: Session,
    source: SourceDocument,
    *,
    settings: Settings,
    checked_by: str,
    force: bool,
    client: httpx.Client | None = None,
) -> SourceCheck:
    if not source.is_active:
        check = _record_failed_check(
            session,
            source,
            checked_by=checked_by,
            forced=force,
            message="Inactive sources cannot be fetched.",
        )
        raise SourceFetchError("source_inactive", check.error or "Source is inactive.", check)

    owns_client = client is None
    http_client = client or httpx.Client(timeout=settings.source_fetch_timeout_seconds)
    try:
        retrieved = retrieve_source(
            http_client,
            source.official_url,
            max_bytes=settings.source_fetch_max_bytes,
            max_redirects=settings.source_fetch_max_redirects,
        )
        kind = _content_kind(retrieved.content, retrieved.mime_type)
        expected_kind = "pdf" if source.mime_type == "application/pdf" else "html"
        if kind != expected_kind:
            raise ValueError(
                f"Expected {expected_kind.upper()} but the response format could not be verified."
            )
    except (httpx.HTTPError, SourceRegistryError, ValueError) as error:
        check = _record_failed_check(
            session,
            source,
            checked_by=checked_by,
            forced=force,
            message=str(error),
        )
        raise SourceFetchError("source_fetch_failed", str(error), check) from error
    finally:
        if owns_client:
            http_client.close()

    checked_at = datetime.now(UTC)
    content_hash = hashlib.sha256(retrieved.content).hexdigest()
    revision = session.scalar(
        select(SourceRevision).where(
            SourceRevision.source_document_id == source.id,
            SourceRevision.content_hash == content_hash,
        )
    )
    if revision is not None and not force:
        revision.last_source_check_at = checked_at
        check = SourceCheck(
            check_id=f"CMS-CHECK-{uuid4().hex}",
            source_document=source,
            source_revision=revision,
            outcome=SourceCheckOutcome.UNCHANGED,
            requested_url=source.official_url,
            final_url=retrieved.final_url,
            http_status=retrieved.http_status,
            mime_type=retrieved.mime_type,
            byte_length=len(retrieved.content),
            content_hash=content_hash,
            forced=False,
            checked_by=checked_by,
        )
        session.add(check)
        session.flush()
        return check

    if revision is None:
        revision_number = (
            session.scalar(
                select(func.max(SourceRevision.revision_number)).where(
                    SourceRevision.source_document_id == source.id
                )
            )
            or 0
        ) + 1
        revision = SourceRevision(
            revision_id=f"{source.source_id}-R{revision_number}-{content_hash[:12]}",
            source_document=source,
            revision_number=revision_number,
            content_hash=content_hash,
            publication_date=None,
            effective_date=None,
            retrieved_at=checked_at,
            last_source_check_at=checked_at,
            source_url=source.official_url,
            final_url=retrieved.final_url,
            http_status=retrieved.http_status,
            retrieved_mime_type=retrieved.mime_type,
            byte_length=len(retrieved.content),
            content_blob=retrieved.content,
            publication_state=PublicationState.DRAFT,
            verification_status=PublicVerificationStatus.PARTIALLY_VERIFIED,
        )
        session.add(revision)
        session.flush()
        outcome = SourceCheckOutcome.NEW_REVISION
    else:
        revision.last_source_check_at = checked_at
        outcome = SourceCheckOutcome.REPROCESSED

    extraction_result = (
        extract_pdf(retrieved.content)
        if expected_kind == "pdf"
        else extract_html(retrieved.content, retrieved.mime_type)
    )
    extraction = _create_extraction(
        session,
        revision,
        extraction_result,
        forced=force,
        checked_by=checked_by,
    )
    check = SourceCheck(
        check_id=f"CMS-CHECK-{uuid4().hex}",
        source_document=source,
        source_revision=revision,
        extraction=extraction,
        outcome=outcome,
        requested_url=source.official_url,
        final_url=retrieved.final_url,
        http_status=retrieved.http_status,
        mime_type=retrieved.mime_type,
        byte_length=len(retrieved.content),
        content_hash=content_hash,
        forced=force,
        checked_by=checked_by,
    )
    session.add(check)
    session.flush()
    return check
