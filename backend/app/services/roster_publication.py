"""Publish the reviewed program-roster baseline without exposing draft specifications."""

from dataclasses import dataclass
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.commands.seed_verified import PROGRAM, _load_seed
from app.domain import (
    AffectedField,
    CollectionType,
    FieldAvailability,
    PublicationState,
    PublicVerificationStatus,
)
from app.models import (
    EvidenceReference,
    Measure,
    MeasureVersion,
    ProgramMembership,
    SourceRevision,
    SpecificationField,
)


class RosterPublicationError(ValueError):
    """Raised when the frozen roster baseline is not safe to publish."""


@dataclass(frozen=True)
class RosterPublicationResult:
    published_measures: int
    published_memberships: int
    published_roster_versions: int
    published_source_revisions: int


def _is_official_cms_url(value: str) -> bool:
    hostname = (urlparse(value).hostname or "").lower()
    return hostname == "cms.gov" or hostname.endswith(".cms.gov")


def _roster_version(session: Session, version_id: str) -> MeasureVersion | None:
    return session.scalar(
        select(MeasureVersion)
        .where(MeasureVersion.version_id == version_id)
        .options(
            selectinload(MeasureVersion.fields)
            .selectinload(SpecificationField.evidence)
            .selectinload(EvidenceReference.source_revision)
            .selectinload(SourceRevision.source_document)
        )
    )


def _validate_roster_version(
    version: MeasureVersion,
    *,
    measure_id: str,
    year: int,
) -> set[SourceRevision]:
    if (
        version.program != PROGRAM
        or version.performance_year != year
        or version.collection_type != CollectionType.PROGRAM_ROSTER
        or not version.is_program_member
        or version.newer_revision_detected
        or version.verified_at is None
    ):
        raise RosterPublicationError(
            f"Roster version is not verified for publication: {version.version_id}"
        )

    if len(version.fields) != 1:
        raise RosterPublicationError(
            f"Roster version must contain only the measure-set field: {version.version_id}"
        )
    field = version.fields[0]
    expected_value = f"Member of the PY{year} MSSP APP Plus quality measure set."
    if (
        field.field != AffectedField.MEASURE_SET
        or field.availability != FieldAvailability.AVAILABLE
        or field.value != expected_value
    ):
        raise RosterPublicationError(
            f"Roster field conflicts with the frozen inventory: {version.version_id}"
        )

    revisions: set[SourceRevision] = set()
    source_document_ids: set[int] = set()
    for evidence in field.evidence:
        revision = evidence.source_revision
        document = revision.source_document
        if (
            not evidence.locator
            or not evidence.locator.strip()
            or not evidence.excerpt.strip()
            or revision.verification_status != PublicVerificationStatus.VERIFIED
            or not document.is_active
            or not _is_official_cms_url(document.official_url)
        ):
            raise RosterPublicationError(
                f"Roster evidence is incomplete or unverified: {measure_id} PY{year}"
            )
        revisions.add(revision)
        source_document_ids.add(document.id)

    if len(source_document_ids) < 2:
        raise RosterPublicationError(
            f"Two distinct official CMS sources are required: {measure_id} PY{year}"
        )
    return revisions


def publish_verified_roster_baseline(session: Session) -> RosterPublicationResult:
    """Publish only frozen identities, memberships, and roster evidence.

    Detailed specification variants and field candidates are intentionally untouched.
    Running the operation repeatedly is safe and returns zero counts after the first run.
    """

    seed = _load_seed()
    measures_published = 0
    memberships_published = 0
    versions_published = 0
    source_revisions_published = 0
    validated: list[tuple[Measure, ProgramMembership, MeasureVersion, set[SourceRevision]]] = []

    for record in seed["measures"]:
        measure = session.scalar(
            select(Measure).where(Measure.measure_id == record["measure_id"])
        )
        if measure is None or measure.name != record["name"]:
            raise RosterPublicationError(
                f"Frozen roster identity is missing or conflicting: {record['measure_id']}"
            )

        for year in record["memberships"]:
            membership = session.scalar(
                select(ProgramMembership).where(
                    ProgramMembership.measure_id == measure.id,
                    ProgramMembership.program == PROGRAM,
                    ProgramMembership.performance_year == year,
                )
            )
            if (
                membership is None
                or not membership.is_program_member
                or membership.verified_at is None
            ):
                raise RosterPublicationError(
                    f"Verified membership is missing: {record['measure_id']} PY{year}"
                )

            version_id = f"CMS-APPPLUS-{record['measure_id']}-PY{year}-ROSTER-R1"
            version = _roster_version(session, version_id)
            if version is None or version.measure_id != measure.id:
                raise RosterPublicationError(f"Roster version is missing: {version_id}")
            revisions = _validate_roster_version(
                version,
                measure_id=record["measure_id"],
                year=year,
            )
            validated.append((measure, membership, version, revisions))

    for measure, membership, version, revisions in validated:
        if not measure.is_public:
            measure.is_public = True
            measures_published += 1
        if membership.publication_state != PublicationState.PUBLISHED:
            membership.publication_state = PublicationState.PUBLISHED
            memberships_published += 1
        if version.publication_state != PublicationState.PUBLISHED:
            version.publication_state = PublicationState.PUBLISHED
            versions_published += 1
        version.verification_status = PublicVerificationStatus.VERIFIED
        for revision in revisions:
            if revision.publication_state != PublicationState.PUBLISHED:
                revision.publication_state = PublicationState.PUBLISHED
                source_revisions_published += 1

    session.flush()
    return RosterPublicationResult(
        published_measures=measures_published,
        published_memberships=memberships_published,
        published_roster_versions=versions_published,
        published_source_revisions=source_revisions_published,
    )
