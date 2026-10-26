"""Rules for promoting one reviewed field without exposing sibling drafts."""

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import (
    AffectedField,
    CandidateReviewDecision,
    FieldAvailability,
    FieldPublicationEligibility,
    PublicationState,
    PublicVerificationStatus,
)
from app.models import (
    EvidenceReference,
    MeasureVersion,
    ProgramMembership,
    SpecificationField,
    SpecificationFieldCandidate,
)

PUBLISHABLE_CANDIDATE_FIELDS: dict[str, AffectedField] = {
    "description": AffectedField.DEFINITION,
    "population_or_denominator": AffectedField.DENOMINATOR,
    "numerator_or_outcome": AffectedField.NUMERATOR,
    "exclusions": AffectedField.EXCLUSIONS,
}


class FieldPublicationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ExplanationEvidenceField:
    field: AffectedField
    value: str
    evidence_ids: tuple[str, ...]


def field_publication_eligibility(
    candidate: SpecificationFieldCandidate,
) -> FieldPublicationEligibility:
    if candidate.publication_state == PublicationState.PUBLISHED:
        return FieldPublicationEligibility.PUBLISHED
    if candidate.review_decision != CandidateReviewDecision.APPROVE:
        return FieldPublicationEligibility.NOT_APPROVED
    if not candidate.source_excerpt or not candidate.source_excerpt.strip():
        return FieldPublicationEligibility.MISSING_SOURCE_EXCERPT
    affected_field = PUBLISHABLE_CANDIDATE_FIELDS.get(candidate.field_name)
    if affected_field is None:
        return FieldPublicationEligibility.UNSUPPORTED_FIELD
    version = candidate.measure_version
    if version.newer_revision_detected:
        return FieldPublicationEligibility.STALE_SOURCE
    if candidate.source_revision.verification_status != PublicVerificationStatus.VERIFIED:
        return FieldPublicationEligibility.UNVERIFIED_SOURCE
    membership = next(
        (
            item
            for item in version.measure.memberships
            if item.program == version.program
            and item.performance_year == version.performance_year
            and item.is_program_member
            and item.verified_at is not None
        ),
        None,
    )
    if membership is None:
        return FieldPublicationEligibility.UNVERIFIED_MEMBERSHIP
    if any(field.field == affected_field for field in version.fields):
        return FieldPublicationEligibility.FIELD_CONFLICT
    return FieldPublicationEligibility.ELIGIBLE


def publication_blocker(eligibility: FieldPublicationEligibility) -> str | None:
    messages = {
        FieldPublicationEligibility.NOT_APPROVED: (
            "A qualified reviewer must approve this candidate before publication."
        ),
        FieldPublicationEligibility.MISSING_SOURCE_EXCERPT: (
            "A reviewer-approved literal source excerpt is required before publication."
        ),
        FieldPublicationEligibility.UNSUPPORTED_FIELD: (
            "This candidate does not yet map safely to the public field contract."
        ),
        FieldPublicationEligibility.STALE_SOURCE: (
            "A newer source revision was detected; re-review is required."
        ),
        FieldPublicationEligibility.UNVERIFIED_SOURCE: (
            "The source revision is not verified for publication."
        ),
        FieldPublicationEligibility.UNVERIFIED_MEMBERSHIP: (
            "Verified program-year membership is required before publication."
        ),
        FieldPublicationEligibility.FIELD_CONFLICT: (
            "This version already has a public value for the mapped field."
        ),
    }
    return messages.get(eligibility)


def _evidence_id(review_item_id: str) -> str:
    digest = sha256(review_item_id.encode("utf-8")).hexdigest()[:24]
    return f"CMS-PUBLISHED-FIELD-{digest}"


def publish_approved_field(
    session: Session,
    candidate: SpecificationFieldCandidate,
    *,
    publisher_name: str,
    published_at: datetime | None = None,
) -> SpecificationFieldCandidate:
    eligibility = field_publication_eligibility(candidate)
    if eligibility == FieldPublicationEligibility.PUBLISHED:
        return candidate
    if eligibility != FieldPublicationEligibility.ELIGIBLE:
        raise FieldPublicationError(
            f"field_publication_{eligibility.value}",
            publication_blocker(eligibility) or "The field is not eligible for publication.",
        )

    version = candidate.measure_version
    affected_field = PUBLISHABLE_CANDIDATE_FIELDS[candidate.field_name]
    publication_time = published_at or datetime.now(UTC)
    field = SpecificationField(
        field=affected_field,
        availability=FieldAvailability.AVAILABLE,
        value=candidate.reviewed_value,
        evidence=[
            EvidenceReference(
                evidence_id=_evidence_id(candidate.review_item_id),
                source_revision=candidate.source_revision,
                locator=candidate.evidence_locator,
                excerpt=candidate.source_excerpt or "",
            )
        ],
    )
    version.fields.append(field)
    session.flush()

    candidate.publication_state = PublicationState.PUBLISHED
    candidate.published_field = field
    candidate.published_at = publication_time
    candidate.published_by = publisher_name

    version.publication_state = PublicationState.PUBLISHED
    version.verification_status = PublicVerificationStatus.PARTIALLY_VERIFIED
    version.verified_at = publication_time
    version.measure.is_public = True
    candidate.source_revision.publication_state = PublicationState.PUBLISHED

    membership = session.scalar(
        select(ProgramMembership).where(
            ProgramMembership.measure_id == version.measure_id,
            ProgramMembership.program == version.program,
            ProgramMembership.performance_year == version.performance_year,
            ProgramMembership.is_program_member.is_(True),
            ProgramMembership.verified_at.is_not(None),
        )
    )
    if membership is None:
        raise FieldPublicationError(
            "field_publication_unverified_membership",
            "Verified program-year membership is required before publication.",
        )
    membership.publication_state = PublicationState.PUBLISHED
    session.flush()
    return candidate


def build_public_explanation_context(
    version: MeasureVersion,
) -> tuple[ExplanationEvidenceField, ...]:
    """Return only published, evidenced facts that a future AI prompt may use."""

    if version.publication_state != PublicationState.PUBLISHED:
        return ()
    context: list[ExplanationEvidenceField] = []
    for field in version.fields:
        if field.availability != FieldAvailability.AVAILABLE or not field.value:
            continue
        evidence_ids = tuple(
            reference.evidence_id
            for reference in field.evidence
            if reference.source_revision.publication_state == PublicationState.PUBLISHED
            and reference.excerpt.strip()
        )
        if not evidence_ids:
            continue
        context.append(
            ExplanationEvidenceField(
                field=field.field,
                value=field.value,
                evidence_ids=evidence_ids,
            )
        )
    return tuple(sorted(context, key=lambda item: item.field.value))
