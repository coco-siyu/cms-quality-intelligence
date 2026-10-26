import hashlib
import re
from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

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
    NormalizedFieldCandidate,
    NormalizedMeasureCandidate,
    SourceExtraction,
    SourceNormalization,
    SourceTextSegment,
    SpecificationFieldCandidate,
)

NORMALIZER_VERSION = "cms-labeled-fields-v1"
PROGRAM = "Medicare Shared Savings Program — APP Plus"
EXPECTED_FIELDS = (
    "measure_title",
    "specification_identifier",
    "description",
    "measure_type",
    "scoring_direction",
    "population_or_denominator",
    "numerator_or_outcome",
    "exclusions",
    "denominator_exceptions",
    "data_collection",
    "risk_adjustment",
)

LABELS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("denominator_exceptions", ("Denominator Exceptions",)),
    ("exclusions", ("Denominator Exclusions", "Exclusions")),
    ("population_or_denominator", ("Initial Population", "Denominator")),
    ("numerator_or_outcome", ("Numerator", "Outcome")),
    ("specification_identifier", ("CMS eCQM ID", "Specification Identifier")),
    ("scoring_direction", ("Improvement Notation", "Scoring Direction")),
    ("data_collection", ("Data Collection", "Collection Type")),
    ("risk_adjustment", ("Risk Adjustment",)),
    ("measure_title", ("Measure Title", "Title")),
    ("measure_type", ("Measure Type",)),
    ("description", ("Description",)),
)
LABEL_TO_FIELD = {
    label.casefold(): field_name for field_name, labels in LABELS for label in labels
}
LABEL_PATTERN = re.compile(
    r"(?<!\w)("
    + "|".join(
        re.escape(label)
        for _field_name, labels in LABELS
        for label in sorted(labels, key=len, reverse=True)
    )
    + r")\s*:?[ \t]*",
    flags=re.IGNORECASE,
)
SPECIFICATION_PATTERN = re.compile(r"\bCMS\d{1,4}v\d+\b", flags=re.IGNORECASE)
QUALITY_ID_PATTERN = re.compile(
    r"\b(?:Quality|Measure)\s+ID\s*[:#-]?\s*(\d{1,4})\b",
    flags=re.IGNORECASE,
)
YEAR_PATTERN = re.compile(
    r"\b(?:PY|Performance\s+Year|Measurement\s+Year)\s*[:#-]?\s*(20\d{2})\b",
    flags=re.IGNORECASE,
)


class SourceNormalizationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class FieldProposal:
    field_name: str
    value: str
    segment: SourceTextSegment


def _clean(value: str, *, limit: int = 8_000) -> str:
    normalized = re.sub(r"\s+", " ", value).strip(" :-\t")
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit].rsplit(" ", maxsplit=1)[0]


def _heading_field(locator: str) -> str | None:
    if not locator.startswith("HTML heading: "):
        return None
    heading = locator.removeprefix("HTML heading: ").strip().casefold()
    return LABEL_TO_FIELD.get(heading)


def _html_proposals(segments: list[SourceTextSegment]) -> dict[str, FieldProposal]:
    proposals: dict[str, FieldProposal] = {}
    active_field: str | None = None
    for segment in sorted(segments, key=lambda item: item.sequence):
        heading_field = _heading_field(segment.locator)
        if heading_field is not None:
            active_field = heading_field
            continue
        if active_field is None or active_field in proposals:
            continue
        if segment.locator.startswith("HTML section: "):
            value = _clean(segment.text)
            if value:
                proposals[active_field] = FieldProposal(active_field, value, segment)
                active_field = None
    return proposals


def _pdf_proposals(segments: list[SourceTextSegment]) -> dict[str, FieldProposal]:
    proposals: dict[str, FieldProposal] = {}
    for segment in sorted(segments, key=lambda item: item.sequence):
        matches = list(LABEL_PATTERN.finditer(segment.text))
        for index, match in enumerate(matches):
            field_name = LABEL_TO_FIELD[match.group(1).casefold()]
            if field_name in proposals:
                continue
            end = matches[index + 1].start() if index + 1 < len(matches) else len(segment.text)
            value = _clean(segment.text[match.end() : end])
            if value:
                proposals[field_name] = FieldProposal(field_name, value, segment)
    return proposals


def _identity_values(extraction: SourceExtraction) -> tuple[set[str], set[str], set[int]]:
    source = extraction.source_revision.source_document
    extracted_text = " ".join(segment.text for segment in extraction.segments)
    identity_text = f"{source.source_id} {source.title} {extracted_text}"
    specification_ids = {
        match.group(0).upper() for match in SPECIFICATION_PATTERN.finditer(identity_text)
    }
    quality_ids = {
        match.group(1).zfill(3) for match in QUALITY_ID_PATTERN.finditer(identity_text)
    }
    years = {int(match.group(1)) for match in YEAR_PATTERN.finditer(identity_text)}
    return specification_ids, quality_ids, years


def _collection_values(text: str) -> set[CollectionType]:
    values: set[CollectionType] = set()
    if re.search(r"\beCQM\b|electronic clinical quality measure", text, re.I):
        values.add(CollectionType.ECQM)
    if re.search(r"\bMIPS\s+CQM\b", text, re.I):
        values.add(CollectionType.MIPS_CQM)
    if re.search(r"\bMedicare\s+CQM\b", text, re.I):
        values.add(CollectionType.MEDICARE_CQM)
    if re.search(r"\bCAHPS\b", text, re.I):
        values.add(CollectionType.CAHPS_SURVEY)
    if re.search(r"administrative claims", text, re.I):
        values.add(CollectionType.ADMINISTRATIVE_CLAIMS)
    return values


def _matched_version(
    session: Session,
    *,
    specification_ids: set[str],
    quality_ids: set[str],
    years: set[int],
    collections: set[CollectionType],
) -> tuple[MeasureVersion | None, NormalizedIdentityStatus, list[str]]:
    issues: list[str] = []
    if len(specification_ids) > 1:
        issues.append(
            "Multiple specification identifiers were detected: "
            + ", ".join(sorted(specification_ids))
        )
    if len(quality_ids) > 1:
        issues.append("Multiple measure IDs were detected: " + ", ".join(sorted(quality_ids)))
    if len(years) > 1:
        issues.append(
            "Multiple performance years were detected: "
            + ", ".join(str(value) for value in sorted(years))
        )
    if len(collections) > 1:
        issues.append(
            "Multiple collection types were detected: "
            + ", ".join(value.value for value in sorted(collections, key=lambda item: item.value))
        )
    if issues:
        return None, NormalizedIdentityStatus.AMBIGUOUS, issues

    candidates: list[MeasureVersion] = []
    if len(specification_ids) == 1:
        specification_id = next(iter(specification_ids))
        statement = select(MeasureVersion).where(
            func.upper(MeasureVersion.specification_identifier) == specification_id,
            MeasureVersion.program == PROGRAM,
        )
        if years:
            statement = statement.where(
                MeasureVersion.performance_year == next(iter(years))
            )
        candidates = list(session.scalars(statement))
    elif len(quality_ids) == 1 and len(years) == 1:
        statement = (
            select(MeasureVersion)
            .join(Measure)
            .where(
                Measure.measure_id == next(iter(quality_ids)),
                MeasureVersion.performance_year == next(iter(years)),
                MeasureVersion.program == PROGRAM,
            )
        )
        if collections:
            statement = statement.where(
                MeasureVersion.collection_type == next(iter(collections))
            )
        candidates = list(session.scalars(statement))

    if len(candidates) == 1:
        return candidates[0], NormalizedIdentityStatus.MATCHED, issues
    if len(candidates) > 1:
        issues.append("The extracted identity matches multiple stored measure versions.")
        return None, NormalizedIdentityStatus.AMBIGUOUS, issues
    issues.append("No exact stored measure version matched the extracted identity.")
    return None, NormalizedIdentityStatus.UNRESOLVED, issues


def _review_item_id(extraction_id: str, version_id: str, field_name: str) -> str:
    digest = hashlib.sha256(
        f"{extraction_id}|{version_id}|{field_name}".encode()
    ).hexdigest()[:32]
    return f"CMS-NORMALIZED-{digest}"


def _stage_field(
    session: Session,
    normalized_field: NormalizedFieldCandidate,
    version: MeasureVersion | None,
    extraction: SourceExtraction,
) -> None:
    if version is None or normalized_field.status != NormalizedFieldStatus.EXTRACTED:
        normalized_field.staging_status = NormalizedStagingStatus.UNMATCHED
        return
    existing = session.scalar(
        select(SpecificationFieldCandidate).where(
            SpecificationFieldCandidate.measure_version_id == version.id,
            SpecificationFieldCandidate.field_name == normalized_field.field_name,
        )
    )
    if existing is not None:
        normalized_field.staged_field_candidate = existing
        if existing.source_revision_id == extraction.source_revision_id:
            normalized_field.staging_status = NormalizedStagingStatus.EXISTING
        else:
            normalized_field.staging_status = (
                NormalizedStagingStatus.BLOCKED_NEWER_REVISION
            )
            version.newer_revision_detected = True
        return

    staged = SpecificationFieldCandidate(
        review_item_id=_review_item_id(
            extraction.extraction_id, version.version_id, normalized_field.field_name
        ),
        measure_version=version,
        field_name=normalized_field.field_name,
        candidate_value=normalized_field.candidate_value or "",
        source_excerpt=normalized_field.source_excerpt,
        extraction_status="candidate_extracted_needs_sme_review",
        source_revision=extraction.source_revision,
        evidence_locator=normalized_field.evidence_locator or "",
        review_decision=CandidateReviewDecision.PENDING,
        publication_state=PublicationState.DRAFT,
    )
    session.add(staged)
    session.flush()
    normalized_field.staged_field_candidate = staged
    normalized_field.staging_status = NormalizedStagingStatus.STAGED


def normalize_extraction(
    session: Session,
    extraction: SourceExtraction,
    *,
    created_by: str,
) -> SourceNormalization:
    if extraction.status != SourceExtractionStatus.EXTRACTED:
        raise SourceNormalizationError(
            "source_extraction_not_ready",
            "Only a successful text extraction can be normalized.",
        )
    existing = session.scalar(
        select(SourceNormalization)
        .where(
            SourceNormalization.source_extraction_id == extraction.id,
            SourceNormalization.parser_version == NORMALIZER_VERSION,
        )
        .options(
            selectinload(SourceNormalization.measure_candidates).selectinload(
                NormalizedMeasureCandidate.fields
            )
        )
    )
    if existing is not None:
        return existing

    segments = sorted(extraction.segments, key=lambda item: item.sequence)
    proposals = (
        _html_proposals(segments)
        if extraction.extractor_version.startswith("stdlib-html")
        else _pdf_proposals(segments)
    )
    specification_ids, quality_ids, years = _identity_values(extraction)
    identity_text = " ".join(segment.text for segment in segments)
    collections = _collection_values(identity_text)

    if not proposals and not specification_ids and not quality_ids:
        normalization = SourceNormalization(
            normalization_id=f"CMS-NORM-{uuid4().hex}",
            source_extraction=extraction,
            parser_version=NORMALIZER_VERSION,
            status=SourceNormalizationStatus.NO_CANDIDATES,
            created_by=created_by,
        )
        session.add(normalization)
        session.flush()
        return normalization

    matched_version, identity_status, issues = _matched_version(
        session,
        specification_ids=specification_ids,
        quality_ids=quality_ids,
        years=years,
        collections=collections,
    )
    unresolved_fields = [field for field in EXPECTED_FIELDS if field not in proposals]
    if unresolved_fields:
        issues.append("Unresolved fields: " + ", ".join(unresolved_fields))

    normalization = SourceNormalization(
        normalization_id=f"CMS-NORM-{uuid4().hex}",
        source_extraction=extraction,
        parser_version=NORMALIZER_VERSION,
        status=(
            SourceNormalizationStatus.NORMALIZED
            if matched_version is not None and proposals
            else SourceNormalizationStatus.NEEDS_REVIEW
        ),
        created_by=created_by,
    )
    measure_candidate = NormalizedMeasureCandidate(
        candidate_id=f"CMS-MEASURE-CANDIDATE-{uuid4().hex}",
        sequence=1,
        identity_status=identity_status,
        measure_id_candidate=(next(iter(quality_ids)) if len(quality_ids) == 1 else None),
        performance_year_candidate=(next(iter(years)) if len(years) == 1 else None),
        collection_type_candidate=(
            next(iter(collections)).value if len(collections) == 1 else None
        ),
        specification_identifier_candidate=(
            next(iter(specification_ids)) if len(specification_ids) == 1 else None
        ),
        matched_measure_version=matched_version,
        issues="\n".join(issues) if issues else None,
    )
    normalization.measure_candidates.append(measure_candidate)

    for field_name in EXPECTED_FIELDS:
        proposal = proposals.get(field_name)
        normalized_field = NormalizedFieldCandidate(
            field_candidate_id=f"CMS-FIELD-CANDIDATE-{uuid4().hex}",
            field_name=field_name,
            candidate_value=proposal.value if proposal else None,
            status=(
                NormalizedFieldStatus.EXTRACTED
                if proposal
                else NormalizedFieldStatus.UNRESOLVED
            ),
            source_text_segment=proposal.segment if proposal else None,
            evidence_locator=proposal.segment.locator if proposal else None,
            source_excerpt=proposal.value if proposal else None,
            staging_status=NormalizedStagingStatus.UNMATCHED,
        )
        measure_candidate.fields.append(normalized_field)
        session.add(normalized_field)
        session.flush()
        _stage_field(session, normalized_field, matched_version, extraction)

    session.add(normalization)
    session.flush()
    return normalization
