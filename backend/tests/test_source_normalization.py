from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.domain import (
    CandidateReviewDecision,
    CollectionType,
    NormalizedFieldStatus,
    NormalizedIdentityStatus,
    NormalizedStagingStatus,
    PublicationState,
    SourceExtractionStatus,
    SourceNormalizationStatus,
)
from app.models import (
    Measure,
    MeasureVersion,
    SourceDocument,
    SourceExtraction,
    SourceRevision,
    SourceTextSegment,
    SpecificationFieldCandidate,
)
from app.services.source_normalization import EXPECTED_FIELDS, normalize_extraction

PROGRAM = "Medicare Shared Savings Program — APP Plus"


def _version(session: Session, *, specification_identifier: str = "CMS122v14") -> MeasureVersion:
    version = MeasureVersion(
        version_id="CMS-001-PY2026-ECQM",
        program=PROGRAM,
        performance_year=2026,
        collection_type=CollectionType.ECQM,
        specification_identifier=specification_identifier,
        version_number=1,
        is_program_member=True,
        publication_state=PublicationState.DRAFT,
        last_source_check_at=datetime(2026, 10, 26, tzinfo=UTC),
    )
    session.add(
        Measure(
            measure_id="001",
            name="Test diabetes measure",
            description="Private normalization test record.",
            is_public=False,
            versions=[version],
        )
    )
    session.flush()
    return version


def _extraction(
    session: Session,
    *,
    revision_id: str = "CMS-NORMALIZATION-SOURCE-R1",
    content_hash: str = "normalization-hash-1",
    identity: str = "CMS eCQM ID CMS122v14. Performance Year 2026. eCQM.",
) -> SourceExtraction:
    source = SourceDocument(
        source_id=f"CMS-PY2026-{revision_id}",
        title="PY2026 official CMS measure specification",
        official_url=f"https://www.cms.gov/test/{revision_id}.html",
        mime_type="text/html",
    )
    revision = SourceRevision(
        revision_id=revision_id,
        revision_number=1,
        content_hash=content_hash,
        retrieved_at=datetime(2026, 10, 26, tzinfo=UTC),
        last_source_check_at=datetime(2026, 10, 26, tzinfo=UTC),
    )
    extraction = SourceExtraction(
        extraction_id=f"{revision_id}-X1",
        sequence=1,
        status=SourceExtractionStatus.EXTRACTED,
        page_count=None,
        extractor_version="stdlib-html-v1",
        forced=False,
        created_by="reviewer",
        segments=[
            SourceTextSegment(
                sequence=1,
                locator="HTML section: Document body",
                text=identity,
            ),
            SourceTextSegment(
                sequence=2,
                locator="HTML heading: Description",
                text="Description",
            ),
            SourceTextSegment(
                sequence=3,
                locator="HTML section: Description",
                text="Percentage of adults with a documented glycemic assessment.",
            ),
            SourceTextSegment(
                sequence=4,
                locator="HTML heading: Numerator",
                text="Numerator",
            ),
            SourceTextSegment(
                sequence=5,
                locator="HTML section: Numerator",
                text="Patients meeting the source-defined numerator criteria.",
            ),
        ],
    )
    revision.extractions.append(extraction)
    source.revisions.append(revision)
    session.add(source)
    session.flush()
    return extraction


def test_exact_identity_stages_only_extracted_fields_and_retains_missing_fields(
    session: Session,
) -> None:
    version = _version(session)
    extraction = _extraction(session)

    normalization = normalize_extraction(
        session, extraction, created_by="reviewer"
    )
    session.commit()

    assert normalization.status == SourceNormalizationStatus.NORMALIZED
    assert len(normalization.measure_candidates) == 1
    candidate = normalization.measure_candidates[0]
    assert candidate.identity_status == NormalizedIdentityStatus.MATCHED
    assert candidate.matched_measure_version is version
    assert len(candidate.fields) == len(EXPECTED_FIELDS)
    extracted = [
        field for field in candidate.fields if field.status == NormalizedFieldStatus.EXTRACTED
    ]
    unresolved = [
        field for field in candidate.fields if field.status == NormalizedFieldStatus.UNRESOLVED
    ]
    assert {field.field_name for field in extracted} == {
        "description",
        "numerator_or_outcome",
    }
    assert len(unresolved) == len(EXPECTED_FIELDS) - 2
    assert all(field.staging_status == NormalizedStagingStatus.STAGED for field in extracted)
    assert all(
        field.staging_status == NormalizedStagingStatus.UNMATCHED
        for field in unresolved
    )

    staged = session.query(SpecificationFieldCandidate).all()
    assert len(staged) == 2
    assert all(item.review_decision == CandidateReviewDecision.PENDING for item in staged)
    assert all(item.publication_state == PublicationState.DRAFT for item in staged)
    assert {item.source_excerpt for item in staged} == {
        "Percentage of adults with a documented glycemic assessment.",
        "Patients meeting the source-defined numerator criteria.",
    }
    assert all(item.source_revision is extraction.source_revision for item in staged)


def test_normalization_is_idempotent_for_one_extraction_and_parser(session: Session) -> None:
    _version(session)
    extraction = _extraction(session)

    first = normalize_extraction(session, extraction, created_by="reviewer")
    second = normalize_extraction(session, extraction, created_by="reviewer")
    session.commit()

    assert second.normalization_id == first.normalization_id
    assert session.query(SpecificationFieldCandidate).count() == 2


def test_ambiguous_identity_is_retained_without_staging(session: Session) -> None:
    _version(session)
    extraction = _extraction(
        session,
        identity=(
            "CMS eCQM IDs CMS122v14 and CMS130v14. "
            "Performance Year 2026. eCQM."
        ),
    )

    normalization = normalize_extraction(
        session, extraction, created_by="reviewer"
    )
    session.commit()

    candidate = normalization.measure_candidates[0]
    assert normalization.status == SourceNormalizationStatus.NEEDS_REVIEW
    assert candidate.identity_status == NormalizedIdentityStatus.AMBIGUOUS
    assert candidate.matched_measure_version is None
    assert "Multiple specification identifiers" in (candidate.issues or "")
    assert all(
        field.staging_status == NormalizedStagingStatus.UNMATCHED
        for field in candidate.fields
    )
    assert session.query(SpecificationFieldCandidate).count() == 0


def test_new_source_revision_never_overwrites_an_existing_review_candidate(
    session: Session,
) -> None:
    version = _version(session)
    old_extraction = _extraction(
        session,
        revision_id="CMS-NORMALIZATION-OLD-R1",
        content_hash="old-content-hash",
    )
    existing = SpecificationFieldCandidate(
        review_item_id="EXISTING-REVIEW-ITEM",
        measure_version=version,
        field_name="description",
        candidate_value="Previously reviewed source wording.",
        source_excerpt="Previously reviewed source wording.",
        extraction_status="candidate_extracted_needs_sme_review",
        source_revision=old_extraction.source_revision,
        evidence_locator="HTML section: Description",
        review_decision=CandidateReviewDecision.PENDING,
        publication_state=PublicationState.DRAFT,
    )
    session.add(existing)
    new_extraction = _extraction(
        session,
        revision_id="CMS-NORMALIZATION-NEW-R2",
        content_hash="new-content-hash",
    )

    normalization = normalize_extraction(
        session, new_extraction, created_by="reviewer"
    )
    session.commit()

    description = next(
        field
        for field in normalization.measure_candidates[0].fields
        if field.field_name == "description"
    )
    assert description.staging_status == NormalizedStagingStatus.BLOCKED_NEWER_REVISION
    assert description.staged_field_candidate is existing
    assert existing.candidate_value == "Previously reviewed source wording."
    assert version.newer_revision_detected is True
    assert session.query(SpecificationFieldCandidate).count() == 2
