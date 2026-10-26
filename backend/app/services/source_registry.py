from datetime import UTC, datetime
from ipaddress import ip_address
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SourceDocument

SOURCE_FORMAT_MIME_TYPES = {
    "html": "text/html",
    "pdf": "application/pdf",
}


class SourceRegistryError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def validate_official_cms_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme.lower() != "https":
        raise SourceRegistryError(
            "source_url_requires_https", "CMS source URLs must use HTTPS."
        )
    if parsed.username or parsed.password:
        raise SourceRegistryError(
            "source_url_userinfo_forbidden", "CMS source URLs cannot contain user information."
        )
    try:
        port = parsed.port
    except ValueError as error:
        raise SourceRegistryError(
            "source_url_invalid_port", "The source URL port is invalid."
        ) from error
    if port not in (None, 443):
        raise SourceRegistryError(
            "source_url_port_forbidden", "CMS source URLs may use only the default HTTPS port."
        )
    hostname = (parsed.hostname or "").lower().rstrip(".")
    try:
        ip_address(hostname)
    except ValueError:
        pass
    else:
        raise SourceRegistryError(
            "source_url_ip_forbidden", "IP-address source URLs are not allowed."
        )
    if hostname != "cms.gov" and not hostname.endswith(".cms.gov"):
        raise SourceRegistryError(
            "source_url_domain_forbidden",
            "Only official cms.gov hosts can be registered.",
        )
    if parsed.fragment:
        raise SourceRegistryError(
            "source_url_fragment_forbidden",
            "Remove URL fragments before registering a CMS source.",
        )
    return value


def create_source(
    session: Session,
    *,
    source_id: str,
    title: str,
    official_url: str,
    source_format: str,
    notes: str | None,
    admin_username: str,
) -> SourceDocument:
    official_url = validate_official_cms_url(official_url)
    if session.scalar(select(SourceDocument).where(SourceDocument.source_id == source_id)):
        raise SourceRegistryError(
            "source_id_conflict", f"Source ID '{source_id}' is already registered."
        )
    if session.scalar(
        select(SourceDocument).where(SourceDocument.official_url == official_url)
    ):
        raise SourceRegistryError(
            "source_url_conflict", "That official CMS URL is already registered."
        )
    source = SourceDocument(
        source_id=source_id,
        title=title.strip(),
        official_url=official_url,
        mime_type=SOURCE_FORMAT_MIME_TYPES[source_format],
        is_active=True,
        notes=notes.strip() if notes else None,
        created_by=admin_username,
    )
    session.add(source)
    session.flush()
    return source


def update_source(
    session: Session,
    source: SourceDocument,
    *,
    title: str | None,
    official_url: str | None,
    source_format: str | None,
    notes: str | None,
    update_notes: bool,
    is_active: bool | None,
) -> SourceDocument:
    if official_url is not None:
        official_url = validate_official_cms_url(official_url)
        conflict = session.scalar(
            select(SourceDocument).where(
                SourceDocument.official_url == official_url,
                SourceDocument.id != source.id,
            )
        )
        if conflict:
            raise SourceRegistryError(
                "source_url_conflict", "That official CMS URL is already registered."
            )
        source.official_url = official_url
    if title is not None:
        source.title = title.strip()
    if source_format is not None:
        source.mime_type = SOURCE_FORMAT_MIME_TYPES[source_format]
    if update_notes:
        source.notes = notes.strip() if notes and notes.strip() else None
    if is_active is not None and is_active != source.is_active:
        source.is_active = is_active
        source.deactivated_at = None if is_active else datetime.now(UTC)
    source.updated_at = datetime.now(UTC)
    session.flush()
    return source
