from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import (
    ChangeEvidenceSide,
    ComparisonEvidenceStatus,
    PublicVerificationStatus,
)
from app.models import MeasureComparison
from app.services.comparison_evidence import (
    build_public_change_record,
    comparison_evidence_issues,
    refresh_comparison_evidence_status,
)


def _comparison(session: Session) -> MeasureComparison:
    comparison = session.scalar(select(MeasureComparison))
    assert comparison is not None
    return comparison


def test_public_change_record_projects_source_backed_excerpts(
    seeded_session: Session,
) -> None:
    comparison = _comparison(seeded_session)

    assert comparison.evidence_status == ComparisonEvidenceStatus.VERIFIED
    assert comparison_evidence_issues(comparison) == ()

    record = build_public_change_record(comparison)

    assert record is not None
    assert record.evidence_status == ComparisonEvidenceStatus.VERIFIED
    assert record.measure_id == "DEMO-001"
    assert record.from_year == 2025
    assert record.to_year == 2026
    assert len(record.fields) == 1
    assert {
        (
            evidence.side,
            evidence.source_revision_id,
            evidence.document_title,
            str(evidence.official_url),
            evidence.locator,
            evidence.excerpt,
        )
        for evidence in record.fields[0].evidence
    } == {
        (
            ChangeEvidenceSide.FROM_VERSION,
            "DEMO-SOURCE-001-R1",
            "Fictional C1 Test Source",
            "https://example.invalid/cms-quality-intelligence/demo-source",
            "Demo section 2025",
            "Fictional evidence excerpt for automated testing only.",
        ),
        (
            ChangeEvidenceSide.TO_VERSION,
            "DEMO-SOURCE-001-R1",
            "Fictional C1 Test Source",
            "https://example.invalid/cms-quality-intelligence/demo-source",
            "Demo section 2026",
            "Fictional evidence excerpt for automated testing only.",
        ),
    }


def test_missing_year_side_makes_comparison_incomplete(
    seeded_session: Session,
) -> None:
    comparison = _comparison(seeded_session)
    comparison_field = comparison.affected_fields[0]
    comparison_field.evidence_links = [
        link
        for link in comparison_field.evidence_links
        if link.side == ChangeEvidenceSide.FROM_VERSION
    ]

    status = refresh_comparison_evidence_status(comparison)
    issues = comparison_evidence_issues(comparison)

    assert status == ComparisonEvidenceStatus.INCOMPLETE
    assert any(
        issue.code == "missing_side_evidence"
        and issue.side == ChangeEvidenceSide.TO_VERSION
        for issue in issues
    )
    assert build_public_change_record(comparison) is None


def test_blank_excerpt_and_locator_cannot_be_verified(
    seeded_session: Session,
) -> None:
    comparison = _comparison(seeded_session)
    reference = comparison.affected_fields[0].evidence_links[0].evidence_reference
    reference.locator = " "
    reference.excerpt = " "

    status = refresh_comparison_evidence_status(comparison)
    issue_codes = {issue.code for issue in comparison_evidence_issues(comparison)}

    assert status == ComparisonEvidenceStatus.INCOMPLETE
    assert {"missing_locator", "missing_excerpt"}.issubset(issue_codes)
    assert build_public_change_record(comparison) is None


def test_unverified_source_revision_cannot_back_public_change(
    seeded_session: Session,
) -> None:
    comparison = _comparison(seeded_session)
    revision = (
        comparison.affected_fields[0]
        .evidence_links[0]
        .evidence_reference.source_revision
    )
    revision.verification_status = PublicVerificationStatus.PARTIALLY_VERIFIED

    status = refresh_comparison_evidence_status(comparison)
    issue_codes = {issue.code for issue in comparison_evidence_issues(comparison)}

    assert status == ComparisonEvidenceStatus.INCOMPLETE
    assert "source_revision_unverified" in issue_codes
    assert build_public_change_record(comparison) is None


def test_evidence_from_wrong_year_version_is_rejected(
    seeded_session: Session,
) -> None:
    comparison = _comparison(seeded_session)
    links = comparison.affected_fields[0].evidence_links
    from_link = next(
        link for link in links if link.side == ChangeEvidenceSide.FROM_VERSION
    )
    to_link = next(link for link in links if link.side == ChangeEvidenceSide.TO_VERSION)
    from_link.evidence_reference = to_link.evidence_reference

    status = refresh_comparison_evidence_status(comparison)
    issue_codes = {issue.code for issue in comparison_evidence_issues(comparison)}

    assert status == ComparisonEvidenceStatus.INCOMPLETE
    assert "evidence_version_mismatch" in issue_codes
    assert build_public_change_record(comparison) is None
