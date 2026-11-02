"""Structural validation and public projection for comparison evidence."""

from dataclasses import dataclass
from urllib.parse import urlparse

from app.domain import (
    AffectedField,
    ChangeEvidenceSide,
    ChangeStatus,
    ComparisonEvidenceStatus,
    PublicationState,
    PublicVerificationStatus,
)
from app.models import MeasureComparison, MeasureComparisonEvidence, MeasureComparisonField
from app.schemas import (
    ChangeFieldEvidenceResponse,
    ChangeFieldResponse,
    PublicChangeRecord,
)


@dataclass(frozen=True)
class ComparisonEvidenceIssue:
    code: str
    field: AffectedField | None
    side: ChangeEvidenceSide | None
    evidence_id: str | None = None


def _is_https_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.hostname)


def _link_issues(
    comparison: MeasureComparison,
    comparison_field: MeasureComparisonField,
    link: MeasureComparisonEvidence,
) -> list[ComparisonEvidenceIssue]:
    reference = link.evidence_reference
    revision = reference.source_revision
    document = revision.source_document
    source_field = reference.specification_field
    source_version = source_field.measure_version
    identity = {
        "field": comparison_field.field,
        "side": link.side,
        "evidence_id": reference.evidence_id,
    }
    issues: list[ComparisonEvidenceIssue] = []

    if not reference.locator or not reference.locator.strip():
        issues.append(ComparisonEvidenceIssue("missing_locator", **identity))
    if not reference.excerpt.strip():
        issues.append(ComparisonEvidenceIssue("missing_excerpt", **identity))
    if revision.publication_state != PublicationState.PUBLISHED:
        issues.append(ComparisonEvidenceIssue("source_revision_unpublished", **identity))
    if revision.verification_status != PublicVerificationStatus.VERIFIED:
        issues.append(ComparisonEvidenceIssue("source_revision_unverified", **identity))
    if not document.is_active:
        issues.append(ComparisonEvidenceIssue("source_document_inactive", **identity))
    if not _is_https_url(document.official_url):
        issues.append(ComparisonEvidenceIssue("source_url_invalid", **identity))
    if source_field.field != comparison_field.field:
        issues.append(ComparisonEvidenceIssue("evidence_field_mismatch", **identity))
    if (
        source_version.publication_state != PublicationState.PUBLISHED
        or source_version.verified_at is None
        or source_version.newer_revision_detected
    ):
        issues.append(ComparisonEvidenceIssue("evidence_version_unverified", **identity))

    expected_year = {
        ChangeEvidenceSide.FROM_VERSION: comparison.from_year,
        ChangeEvidenceSide.TO_VERSION: comparison.to_year,
    }.get(link.side)
    if (
        source_version.measure_id != comparison.measure_id
        or source_version.program != comparison.program
        or source_version.collection_type != comparison.collection_type
        or (expected_year is not None and source_version.performance_year != expected_year)
    ):
        issues.append(ComparisonEvidenceIssue("evidence_version_mismatch", **identity))
    return issues


def comparison_evidence_issues(
    comparison: MeasureComparison,
) -> tuple[ComparisonEvidenceIssue, ...]:
    """Return every reason a comparison is not safe to present as evidenced."""

    issues: list[ComparisonEvidenceIssue] = []
    if not comparison.affected_fields:
        issues.append(
            ComparisonEvidenceIssue(
                code="comparison_has_no_fields",
                field=None,
                side=None,
            )
        )
    if comparison.status != ChangeStatus.UNKNOWN and any(
        field.status == ChangeStatus.UNKNOWN for field in comparison.affected_fields
    ):
        issues.append(
            ComparisonEvidenceIssue(
                code="comparison_contains_unknown_field",
                field=None,
                side=None,
            )
        )

    for field in comparison.affected_fields:
        links_by_side = {
            side: [link for link in field.evidence_links if link.side == side]
            for side in (
                ChangeEvidenceSide.FROM_VERSION,
                ChangeEvidenceSide.TO_VERSION,
            )
        }
        for side, links in links_by_side.items():
            if not links:
                issues.append(
                    ComparisonEvidenceIssue(
                        code="missing_side_evidence",
                        field=field.field,
                        side=side,
                    )
                )
        for link in field.evidence_links:
            issues.extend(_link_issues(comparison, field, link))
    return tuple(issues)


def refresh_comparison_evidence_status(
    comparison: MeasureComparison,
) -> ComparisonEvidenceStatus:
    """Recompute structural coverage without approving or publishing the record."""

    comparison.evidence_status = (
        ComparisonEvidenceStatus.INCOMPLETE
        if comparison_evidence_issues(comparison)
        else ComparisonEvidenceStatus.VERIFIED
    )
    return comparison.evidence_status


def _evidence_response(
    link: MeasureComparisonEvidence,
) -> ChangeFieldEvidenceResponse:
    reference = link.evidence_reference
    revision = reference.source_revision
    document = revision.source_document
    return ChangeFieldEvidenceResponse(
        evidence_id=reference.evidence_id,
        source_revision_id=revision.revision_id,
        document_title=document.title,
        official_url=document.official_url,
        locator=reference.locator,
        excerpt=reference.excerpt,
        side=link.side,
    )


def build_public_change_record(
    comparison: MeasureComparison,
) -> PublicChangeRecord | None:
    """Project only a published comparison with currently valid evidence."""

    if (
        comparison.publication_state != PublicationState.PUBLISHED
        or comparison.evidence_status != ComparisonEvidenceStatus.VERIFIED
        or comparison_evidence_issues(comparison)
    ):
        return None
    fields = [
        ChangeFieldResponse(
            field=field.field,
            status=field.status,
            from_availability=field.from_availability,
            to_availability=field.to_availability,
            from_value=field.from_value,
            to_value=field.to_value,
            evidence=[
                _evidence_response(link)
                for link in sorted(
                    field.evidence_links,
                    key=lambda item: (
                        item.side.value,
                        item.evidence_reference.evidence_id,
                    ),
                )
            ],
        )
        for field in sorted(
            comparison.affected_fields, key=lambda item: item.field.value
        )
    ]
    return PublicChangeRecord(
        measure_id=comparison.measure.measure_id,
        program=comparison.program,
        collection_type=comparison.collection_type,
        from_year=comparison.from_year,
        to_year=comparison.to_year,
        status=comparison.status,
        evidence_status=comparison.evidence_status,
        fields=fields,
    )
