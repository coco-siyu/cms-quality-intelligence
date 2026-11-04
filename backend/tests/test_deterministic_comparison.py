from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from app.domain import (
    AffectedField,
    ChangeEvidenceSide,
    ChangeStatus,
    CollectionType,
    ComparisonEvidenceStatus,
    ComparisonReviewDecision,
    FieldAvailability,
    PublicationState,
    PublicVerificationStatus,
)
from app.models import (
    EvidenceReference,
    Measure,
    MeasureVersion,
    SourceDocument,
    SourceRevision,
    SpecificationField,
)
from app.services.deterministic_comparison import (
    DeterministicComparisonError,
    compare_measure_versions,
    compare_specification_field,
    generate_draft_comparison,
)

CHECKED_AT = datetime(2026, 11, 2, 12, tzinfo=UTC)


def _field(
    field: AffectedField,
    availability: FieldAvailability,
    value: str | None = None,
) -> SpecificationField:
    return SpecificationField(field=field, availability=availability, value=value)


@pytest.mark.parametrize(
    ("from_field", "to_field", "expected"),
    [
        (
            _field(AffectedField.NUMERATOR, FieldAvailability.AVAILABLE, "Same"),
            _field(AffectedField.NUMERATOR, FieldAvailability.AVAILABLE, "Same"),
            ChangeStatus.UNCHANGED,
        ),
        (
            _field(AffectedField.NUMERATOR, FieldAvailability.AVAILABLE, "Before"),
            _field(AffectedField.NUMERATOR, FieldAvailability.AVAILABLE, "After"),
            ChangeStatus.MODIFIED,
        ),
        (
            _field(AffectedField.NUMERATOR, FieldAvailability.UNAVAILABLE),
            _field(AffectedField.NUMERATOR, FieldAvailability.AVAILABLE, "Introduced"),
            ChangeStatus.ADDED,
        ),
        (
            _field(AffectedField.NUMERATOR, FieldAvailability.AVAILABLE, "Retired"),
            _field(AffectedField.NUMERATOR, FieldAvailability.UNAVAILABLE),
            ChangeStatus.REMOVED,
        ),
        (
            _field(AffectedField.NUMERATOR, FieldAvailability.UNAVAILABLE),
            _field(AffectedField.NUMERATOR, FieldAvailability.UNAVAILABLE),
            ChangeStatus.UNCHANGED,
        ),
        (
            _field(AffectedField.NUMERATOR, FieldAvailability.UNRESOLVED),
            _field(AffectedField.NUMERATOR, FieldAvailability.AVAILABLE, "Candidate"),
            ChangeStatus.UNKNOWN,
        ),
        (
            None,
            _field(AffectedField.NUMERATOR, FieldAvailability.AVAILABLE, "Candidate"),
            ChangeStatus.UNKNOWN,
        ),
        (
            _field(AffectedField.NUMERATOR, FieldAvailability.AVAILABLE, "Candidate"),
            None,
            ChangeStatus.UNKNOWN,
        ),
    ],
)
def test_field_comparison_covers_explicit_and_missing_states(
    from_field: SpecificationField | None,
    to_field: SpecificationField | None,
    expected: ChangeStatus,
) -> None:
    result = compare_specification_field(
        AffectedField.NUMERATOR, from_field, to_field
    )

    assert result.status == expected


def test_text_comparison_is_exact_and_never_infers_wording_only() -> None:
    result = compare_specification_field(
        AffectedField.DEFINITION,
        _field(AffectedField.DEFINITION, FieldAvailability.AVAILABLE, "Same wording"),
        _field(AffectedField.DEFINITION, FieldAvailability.AVAILABLE, "Same  wording"),
    )

    assert result.status == ChangeStatus.MODIFIED


def _version(
    measure: Measure,
    year: int,
    *,
    fields: list[SpecificationField],
    is_program_member: bool = True,
    program: str = "Fictional Quality Program",
    collection_type: CollectionType = CollectionType.ECQM,
) -> MeasureVersion:
    version = MeasureVersion(
        version_id=f"{measure.measure_id}-{year}-{collection_type.value}",
        program=program,
        performance_year=year,
        collection_type=collection_type,
        version_number=1,
        is_program_member=is_program_member,
        publication_state=PublicationState.PUBLISHED,
        verification_status=PublicVerificationStatus.PARTIALLY_VERIFIED,
        verified_at=CHECKED_AT,
        last_source_check_at=CHECKED_AT,
        newer_revision_detected=False,
        fields=fields,
    )
    measure.versions.append(version)
    return version


def test_version_comparison_uses_membership_not_year_specific_roster_wording() -> None:
    measure = Measure(
        measure_id="DEMO-VERSION-COMPARE",
        name="Version comparison fixture",
        description="Synthetic test record.",
        is_public=False,
    )
    from_version = _version(
        measure,
        2025,
        fields=[
            _field(
                AffectedField.MEASURE_SET,
                FieldAvailability.AVAILABLE,
                "Member of the fictional PY2025 set.",
            ),
            _field(AffectedField.DENOMINATOR, FieldAvailability.AVAILABLE, "Before"),
        ],
    )
    to_version = _version(
        measure,
        2026,
        fields=[
            _field(
                AffectedField.MEASURE_SET,
                FieldAvailability.AVAILABLE,
                "Member of the fictional PY2026 set.",
            ),
            _field(AffectedField.DENOMINATOR, FieldAvailability.AVAILABLE, "After"),
        ],
    )

    result = compare_measure_versions(
        from_version,
        to_version,
        fields=(AffectedField.MEASURE_SET, AffectedField.DENOMINATOR),
    )

    assert result.status == ChangeStatus.MODIFIED
    assert result.fields[0].status == ChangeStatus.UNCHANGED
    assert result.fields[1].status == ChangeStatus.MODIFIED


def test_unknown_required_field_takes_overall_precedence() -> None:
    measure = Measure(
        measure_id="DEMO-UNKNOWN-COMPARE",
        name="Unknown comparison fixture",
        description="Synthetic test record.",
        is_public=False,
    )
    from_version = _version(
        measure,
        2025,
        fields=[
            _field(AffectedField.NUMERATOR, FieldAvailability.AVAILABLE, "Before")
        ],
    )
    to_version = _version(
        measure,
        2026,
        fields=[_field(AffectedField.NUMERATOR, FieldAvailability.AVAILABLE, "After")],
    )

    result = compare_measure_versions(
        from_version,
        to_version,
        fields=(AffectedField.NUMERATOR, AffectedField.ELIGIBILITY),
    )

    assert [field.status for field in result.fields] == [
        ChangeStatus.MODIFIED,
        ChangeStatus.UNKNOWN,
    ]
    assert result.status == ChangeStatus.UNKNOWN


def test_version_comparison_rejects_collection_variant_mismatch() -> None:
    measure = Measure(
        measure_id="DEMO-VARIANT-COMPARE",
        name="Variant comparison fixture",
        description="Synthetic test record.",
        is_public=False,
    )
    from_version = _version(measure, 2025, fields=[], collection_type=CollectionType.ECQM)
    to_version = _version(
        measure, 2026, fields=[], collection_type=CollectionType.MIPS_CQM
    )

    with pytest.raises(DeterministicComparisonError) as error:
        compare_measure_versions(from_version, to_version)

    assert error.value.code == "comparison_variant_mismatch"


def test_version_comparison_rejects_different_transient_measure_identities() -> None:
    first_measure = Measure(
        measure_id="DEMO-FIRST-IDENTITY",
        name="First identity",
        description="Synthetic test record.",
        is_public=False,
    )
    second_measure = Measure(
        measure_id="DEMO-SECOND-IDENTITY",
        name="Second identity",
        description="Synthetic test record.",
        is_public=False,
    )
    from_version = _version(first_measure, 2025, fields=[])
    to_version = _version(second_measure, 2026, fields=[])

    with pytest.raises(DeterministicComparisonError) as error:
        compare_measure_versions(from_version, to_version)

    assert error.value.code == "comparison_measure_mismatch"


def test_membership_change_requires_explicit_availability_on_both_sides() -> None:
    measure = Measure(
        measure_id="DEMO-MEMBERSHIP-COMPARE",
        name="Membership comparison fixture",
        description="Synthetic test record.",
        is_public=False,
    )
    from_version = _version(
        measure,
        2025,
        is_program_member=False,
        fields=[_field(AffectedField.MEASURE_SET, FieldAvailability.UNAVAILABLE)],
    )
    to_version = _version(
        measure,
        2026,
        is_program_member=True,
        fields=[
            _field(
                AffectedField.MEASURE_SET,
                FieldAvailability.AVAILABLE,
                "Explicitly added to the fictional set.",
            )
        ],
    )

    result = compare_measure_versions(
        from_version, to_version, fields=(AffectedField.MEASURE_SET,)
    )

    assert result.fields[0].status == ChangeStatus.ADDED
    assert result.status == ChangeStatus.ADDED


def test_version_comparison_rejects_unverified_inputs() -> None:
    measure = Measure(
        measure_id="DEMO-UNVERIFIED-COMPARE",
        name="Unverified comparison fixture",
        description="Synthetic test record.",
        is_public=False,
    )
    from_version = _version(measure, 2025, fields=[])
    to_version = _version(measure, 2026, fields=[])
    to_version.verified_at = None

    with pytest.raises(DeterministicComparisonError) as error:
        compare_measure_versions(from_version, to_version)

    assert error.value.code == "comparison_version_unverified"


def _source() -> tuple[SourceDocument, SourceRevision]:
    document = SourceDocument(
        source_id="DEMO-COMPARISON-SOURCE",
        title="Fictional deterministic comparison source",
        official_url="https://example.invalid/deterministic-comparison",
        mime_type="text/html",
    )
    revision = SourceRevision(
        revision_id="DEMO-COMPARISON-SOURCE-R1",
        revision_number=1,
        content_hash="comparison-source-hash",
        retrieved_at=CHECKED_AT,
        last_source_check_at=CHECKED_AT,
        publication_state=PublicationState.PUBLISHED,
        verification_status=PublicVerificationStatus.VERIFIED,
    )
    document.revisions.append(revision)
    return document, revision


def test_generation_persists_an_idempotent_private_draft_with_evidence(
    session: Session,
) -> None:
    document, revision = _source()
    measure = Measure(
        measure_id="DEMO-PERSISTED-COMPARISON",
        name="Persisted comparison fixture",
        description="Synthetic test record.",
        is_public=False,
    )
    for year, value in ((2025, "Before"), (2026, "After")):
        field = _field(AffectedField.DENOMINATOR, FieldAvailability.AVAILABLE, value)
        field.evidence.append(
            EvidenceReference(
                evidence_id=f"DEMO-COMPARISON-EVIDENCE-{year}",
                source_revision=revision,
                locator=f"Fictional section {year}",
                excerpt=f"Fictional excerpt {year}.",
            )
        )
        _version(measure, year, fields=[field])
    session.add_all([document, measure])
    session.commit()

    comparison = generate_draft_comparison(
        session,
        measure_id=measure.measure_id,
        program="Fictional Quality Program",
        from_year=2025,
        to_year=2026,
        collection_type=CollectionType.ECQM,
        fields=(AffectedField.DENOMINATOR,),
    )
    repeated = generate_draft_comparison(
        session,
        measure_id=measure.measure_id,
        program="Fictional Quality Program",
        from_year=2025,
        to_year=2026,
        collection_type=CollectionType.ECQM,
        fields=(AffectedField.DENOMINATOR,),
    )

    assert repeated.id == comparison.id
    assert comparison.publication_state == PublicationState.DRAFT
    assert comparison.status == ChangeStatus.MODIFIED
    assert comparison.collection_type == CollectionType.ECQM
    assert comparison.evidence_status == ComparisonEvidenceStatus.VERIFIED
    assert {link.side for link in comparison.affected_fields[0].evidence_links} == {
        ChangeEvidenceSide.FROM_VERSION,
        ChangeEvidenceSide.TO_VERSION,
    }

    comparison.publication_state = PublicationState.PUBLISHED
    comparison.review_decision = ComparisonReviewDecision.APPROVE
    comparison.reviewed_at = CHECKED_AT
    comparison.reviewer_name = "fixture-reviewer"
    comparison.published_at = CHECKED_AT
    comparison.published_by = "fixture-reviewer"
    session.flush()
    with pytest.raises(DeterministicComparisonError) as error:
        generate_draft_comparison(
            session,
            measure_id=measure.measure_id,
            program="Fictional Quality Program",
            from_year=2025,
            to_year=2026,
            collection_type=CollectionType.ECQM,
            fields=(AffectedField.DENOMINATOR,),
        )
    assert error.value.code == "comparison_record_conflict"


def test_missing_version_is_not_inferred_as_removal(session: Session) -> None:
    measure = Measure(
        measure_id="DEMO-MISSING-VERSION",
        name="Missing version fixture",
        description="Synthetic test record.",
        is_public=False,
    )
    _version(
        measure,
        2025,
        fields=[_field(AffectedField.NUMERATOR, FieldAvailability.AVAILABLE, "Before")],
    )
    session.add(measure)
    session.commit()

    with pytest.raises(DeterministicComparisonError) as error:
        generate_draft_comparison(
            session,
            measure_id=measure.measure_id,
            program="Fictional Quality Program",
            from_year=2025,
            to_year=2026,
            collection_type=CollectionType.ECQM,
            fields=(AffectedField.NUMERATOR,),
        )

    assert error.value.code == "comparison_version_missing"
    assert measure.comparisons == []
