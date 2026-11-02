"""Deterministic comparison of approved measure-version fields.

This module deliberately does not decide whether changed wording is semantically
equivalent. Textual inequality is ``modified`` until a later reviewed semantic
classification says otherwise.
"""

from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain import (
    AffectedField,
    ChangeEvidenceSide,
    ChangeStatus,
    CollectionType,
    FieldAvailability,
    PublicationState,
)
from app.models import (
    EvidenceReference,
    Measure,
    MeasureComparison,
    MeasureComparisonEvidence,
    MeasureComparisonField,
    MeasureVersion,
    SpecificationField,
)
from app.services.comparison_evidence import refresh_comparison_evidence_status


class DeterministicComparisonError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class DeterministicFieldResult:
    field: AffectedField
    status: ChangeStatus
    from_availability: FieldAvailability
    to_availability: FieldAvailability
    from_value: str | None
    to_value: str | None
    from_evidence: tuple[EvidenceReference, ...]
    to_evidence: tuple[EvidenceReference, ...]


@dataclass(frozen=True)
class DeterministicComparisonResult:
    measure_id: str
    program: str
    collection_type: CollectionType
    from_year: int
    to_year: int
    status: ChangeStatus
    fields: tuple[DeterministicFieldResult, ...]


def compare_specification_field(
    field: AffectedField,
    from_field: SpecificationField | None,
    to_field: SpecificationField | None,
) -> DeterministicFieldResult:
    """Compare one normalized field without inferring facts from missing rows."""

    for candidate in (from_field, to_field):
        if candidate is not None and candidate.field != field:
            raise DeterministicComparisonError(
                "comparison_field_mismatch",
                f"Expected {field.value}, received {candidate.field.value}.",
            )

    from_availability = (
        from_field.availability if from_field else FieldAvailability.UNRESOLVED
    )
    to_availability = to_field.availability if to_field else FieldAvailability.UNRESOLVED
    from_value = from_field.value if from_field else None
    to_value = to_field.value if to_field else None

    if (
        from_availability == FieldAvailability.UNRESOLVED
        or to_availability == FieldAvailability.UNRESOLVED
    ):
        status = ChangeStatus.UNKNOWN
    elif (
        from_availability == FieldAvailability.UNAVAILABLE
        and to_availability == FieldAvailability.AVAILABLE
    ):
        status = ChangeStatus.ADDED
    elif (
        from_availability == FieldAvailability.AVAILABLE
        and to_availability == FieldAvailability.UNAVAILABLE
    ):
        status = ChangeStatus.REMOVED
    elif (
        from_availability == FieldAvailability.UNAVAILABLE
        and to_availability == FieldAvailability.UNAVAILABLE
    ):
        status = ChangeStatus.UNCHANGED
    elif from_value is None or to_value is None:
        status = ChangeStatus.UNKNOWN
    elif from_value == to_value:
        status = ChangeStatus.UNCHANGED
    else:
        status = ChangeStatus.MODIFIED

    return DeterministicFieldResult(
        field=field,
        status=status,
        from_availability=from_availability,
        to_availability=to_availability,
        from_value=from_value,
        to_value=to_value,
        from_evidence=tuple(from_field.evidence) if from_field else (),
        to_evidence=tuple(to_field.evidence) if to_field else (),
    )


def _compare_membership_field(
    from_version: MeasureVersion,
    to_version: MeasureVersion,
    from_field: SpecificationField | None,
    to_field: SpecificationField | None,
) -> DeterministicFieldResult:
    result = compare_specification_field(
        AffectedField.MEASURE_SET, from_field, to_field
    )
    expected_from = (
        FieldAvailability.AVAILABLE
        if from_version.is_program_member
        else FieldAvailability.UNAVAILABLE
    )
    expected_to = (
        FieldAvailability.AVAILABLE
        if to_version.is_program_member
        else FieldAvailability.UNAVAILABLE
    )
    if (
        result.from_availability != expected_from
        or result.to_availability != expected_to
    ):
        status = ChangeStatus.UNKNOWN
    elif not from_version.is_program_member and to_version.is_program_member:
        status = ChangeStatus.ADDED
    elif from_version.is_program_member and not to_version.is_program_member:
        status = ChangeStatus.REMOVED
    else:
        status = ChangeStatus.UNCHANGED
    return DeterministicFieldResult(
        field=result.field,
        status=status,
        from_availability=result.from_availability,
        to_availability=result.to_availability,
        from_value=result.from_value,
        to_value=result.to_value,
        from_evidence=result.from_evidence,
        to_evidence=result.to_evidence,
    )


def _overall_status(fields: tuple[DeterministicFieldResult, ...]) -> ChangeStatus:
    if not fields or any(field.status == ChangeStatus.UNKNOWN for field in fields):
        return ChangeStatus.UNKNOWN
    membership = next(
        (field for field in fields if field.field == AffectedField.MEASURE_SET), None
    )
    if membership and membership.status in {ChangeStatus.ADDED, ChangeStatus.REMOVED}:
        return membership.status
    if any(
        field.status in {ChangeStatus.ADDED, ChangeStatus.REMOVED, ChangeStatus.MODIFIED}
        for field in fields
    ):
        return ChangeStatus.MODIFIED
    if any(field.status == ChangeStatus.WORDING_ONLY for field in fields):
        return ChangeStatus.WORDING_ONLY
    return ChangeStatus.UNCHANGED


def _validate_version_pair(
    from_version: MeasureVersion,
    to_version: MeasureVersion,
) -> None:
    same_persisted_measure = (
        from_version.measure_id is not None
        and from_version.measure_id == to_version.measure_id
    )
    same_transient_measure = (
        from_version.measure_id is None
        and to_version.measure_id is None
        and from_version.measure.measure_id == to_version.measure.measure_id
    )
    if not same_persisted_measure and not same_transient_measure:
        raise DeterministicComparisonError(
            "comparison_measure_mismatch",
            "Versions must belong to the same normalized measure identity.",
        )
    if from_version.program != to_version.program:
        raise DeterministicComparisonError(
            "comparison_program_mismatch", "Versions must belong to the same program."
        )
    if from_version.collection_type != to_version.collection_type:
        raise DeterministicComparisonError(
            "comparison_variant_mismatch",
            "Versions must use the same collection variant.",
        )
    if from_version.performance_year == to_version.performance_year:
        raise DeterministicComparisonError(
            "comparison_year_mismatch", "Comparison years must be different."
        )
    for version in (from_version, to_version):
        if (
            version.publication_state != PublicationState.PUBLISHED
            or version.verified_at is None
            or version.newer_revision_detected
        ):
            raise DeterministicComparisonError(
                "comparison_version_unverified",
                f"Version is not approved and current: {version.version_id}",
            )


def compare_measure_versions(
    from_version: MeasureVersion,
    to_version: MeasureVersion,
    *,
    fields: Iterable[AffectedField] = tuple(AffectedField),
) -> DeterministicComparisonResult:
    """Return an exact, deterministic comparison of two approved versions."""

    _validate_version_pair(from_version, to_version)
    selected_fields = tuple(dict.fromkeys(fields))
    if not selected_fields:
        raise DeterministicComparisonError(
            "comparison_fields_empty", "At least one field must be compared."
        )

    from_fields = {field.field: field for field in from_version.fields}
    to_fields = {field.field: field for field in to_version.fields}
    results: list[DeterministicFieldResult] = []
    for field in selected_fields:
        if field == AffectedField.MEASURE_SET:
            result = _compare_membership_field(
                from_version,
                to_version,
                from_fields.get(field),
                to_fields.get(field),
            )
        else:
            result = compare_specification_field(
                field, from_fields.get(field), to_fields.get(field)
            )
        results.append(result)

    measure_id = from_version.measure.measure_id
    field_results = tuple(results)
    return DeterministicComparisonResult(
        measure_id=measure_id,
        program=from_version.program,
        collection_type=from_version.collection_type,
        from_year=from_version.performance_year,
        to_year=to_version.performance_year,
        status=_overall_status(field_results),
        fields=field_results,
    )


def _version_for_comparison(
    session: Session,
    *,
    measure_pk: int,
    program: str,
    performance_year: int,
    collection_type: CollectionType,
) -> MeasureVersion | None:
    return session.scalar(
        select(MeasureVersion)
        .where(
            MeasureVersion.measure_id == measure_pk,
            MeasureVersion.program == program,
            MeasureVersion.performance_year == performance_year,
            MeasureVersion.collection_type == collection_type,
            MeasureVersion.publication_state == PublicationState.PUBLISHED,
            MeasureVersion.verified_at.is_not(None),
            MeasureVersion.newer_revision_detected.is_(False),
        )
        .options(
            selectinload(MeasureVersion.measure),
            selectinload(MeasureVersion.fields).selectinload(
                SpecificationField.evidence
            ),
        )
        .order_by(MeasureVersion.version_number.desc())
        .limit(1)
    )


def _result_signature(
    result: DeterministicComparisonResult,
) -> tuple[object, ...]:
    return (
        result.status,
        tuple(
            (
                field.field,
                field.status,
                field.from_availability,
                field.to_availability,
                field.from_value,
                field.to_value,
                tuple(
                    sorted(
                        (
                            (item.id, ChangeEvidenceSide.FROM_VERSION)
                            for item in field.from_evidence
                        ),
                        key=lambda item: item[0],
                    )
                ),
                tuple(
                    sorted(
                        (
                            (item.id, ChangeEvidenceSide.TO_VERSION)
                            for item in field.to_evidence
                        ),
                        key=lambda item: item[0],
                    )
                ),
            )
            for field in sorted(result.fields, key=lambda item: item.field.value)
        ),
    )


def _stored_signature(comparison: MeasureComparison) -> tuple[object, ...]:
    fields = []
    for field in sorted(comparison.affected_fields, key=lambda item: item.field.value):
        from_evidence = tuple(
            sorted(
                (
                    (link.evidence_reference_id, link.side)
                    for link in field.evidence_links
                    if link.side == ChangeEvidenceSide.FROM_VERSION
                ),
                key=lambda item: item[0],
            )
        )
        to_evidence = tuple(
            sorted(
                (
                    (link.evidence_reference_id, link.side)
                    for link in field.evidence_links
                    if link.side == ChangeEvidenceSide.TO_VERSION
                ),
                key=lambda item: item[0],
            )
        )
        fields.append(
            (
                field.field,
                field.status,
                field.from_availability,
                field.to_availability,
                field.from_value,
                field.to_value,
                from_evidence,
                to_evidence,
            )
        )
    return comparison.status, tuple(fields)


def generate_draft_comparison(
    session: Session,
    *,
    measure_id: str,
    program: str,
    from_year: int,
    to_year: int,
    collection_type: CollectionType,
    fields: Iterable[AffectedField] = tuple(AffectedField),
) -> MeasureComparison:
    """Generate an idempotent private draft without overwriting prior findings."""

    measure = session.scalar(select(Measure).where(Measure.measure_id == measure_id))
    if measure is None:
        raise DeterministicComparisonError(
            "comparison_measure_not_found", f"Measure was not found: {measure_id}"
        )
    from_version = _version_for_comparison(
        session,
        measure_pk=measure.id,
        program=program,
        performance_year=from_year,
        collection_type=collection_type,
    )
    to_version = _version_for_comparison(
        session,
        measure_pk=measure.id,
        program=program,
        performance_year=to_year,
        collection_type=collection_type,
    )
    if from_version is None or to_version is None:
        raise DeterministicComparisonError(
            "comparison_version_missing",
            "Both approved year versions are required; a missing version is not a removal.",
        )

    result = compare_measure_versions(from_version, to_version, fields=fields)
    session.flush()
    existing = session.scalar(
        select(MeasureComparison)
        .where(
            MeasureComparison.measure_id == measure.id,
            MeasureComparison.program == program,
            MeasureComparison.from_year == from_year,
            MeasureComparison.to_year == to_year,
            MeasureComparison.collection_type == collection_type,
        )
        .options(
            selectinload(MeasureComparison.affected_fields).selectinload(
                MeasureComparisonField.evidence_links
            )
        )
    )
    if existing is not None:
        refresh_comparison_evidence_status(existing)
        if (
            existing.publication_state == PublicationState.DRAFT
            and _stored_signature(existing) == _result_signature(result)
        ):
            return existing
        raise DeterministicComparisonError(
            "comparison_record_conflict",
            "An existing comparison would be overwritten; create a reviewed revision instead.",
        )

    comparison = MeasureComparison(
        measure=measure,
        program=program,
        from_year=from_year,
        to_year=to_year,
        collection_type=collection_type,
        status=result.status,
        publication_state=PublicationState.DRAFT,
    )
    for field_result in result.fields:
        comparison_field = MeasureComparisonField(
            field=field_result.field,
            status=field_result.status,
            from_availability=field_result.from_availability,
            to_availability=field_result.to_availability,
            from_value=field_result.from_value,
            to_value=field_result.to_value,
        )
        comparison_field.evidence_links.extend(
            MeasureComparisonEvidence(
                evidence_reference=evidence,
                side=ChangeEvidenceSide.FROM_VERSION,
            )
            for evidence in field_result.from_evidence
        )
        comparison_field.evidence_links.extend(
            MeasureComparisonEvidence(
                evidence_reference=evidence,
                side=ChangeEvidenceSide.TO_VERSION,
            )
            for evidence in field_result.to_evidence
        )
        comparison.affected_fields.append(comparison_field)
    session.add(comparison)
    session.flush()
    refresh_comparison_evidence_status(comparison)
    session.flush()
    return comparison
