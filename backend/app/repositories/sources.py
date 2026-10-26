from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain import NormalizedStagingStatus
from app.models import (
    AIClarificationEvidence,
    AIClarificationProposal,
    NormalizedFieldCandidate,
    NormalizedMeasureCandidate,
    SourceCheck,
    SourceDocument,
    SourceExtraction,
    SourceNormalization,
    SourceRevision,
)
from app.schemas import (
    AdminClarificationEvidenceResponse,
    AdminClarificationProposalResponse,
    AdminNormalizedFieldResponse,
    AdminNormalizedMeasureCandidateResponse,
    AdminSourceCheckResponse,
    AdminSourceDetailResponse,
    AdminSourceExtractionDetailResponse,
    AdminSourceExtractionResponse,
    AdminSourceListResponse,
    AdminSourceNormalizationDetailResponse,
    AdminSourceNormalizationSummaryResponse,
    AdminSourceRevisionResponse,
    AdminSourceSegmentResponse,
    AdminSourceSummaryResponse,
)


def clarification_response(
    proposal: AIClarificationProposal,
) -> AdminClarificationProposalResponse:
    return AdminClarificationProposalResponse(
        clarification_id=proposal.clarification_id,
        field_candidate_id=proposal.normalized_field_candidate.field_candidate_id,
        outcome=proposal.outcome,
        proposed_value=proposal.proposed_value,
        summary=proposal.summary,
        provider=proposal.provider,
        model=proposal.model,
        prompt_version=proposal.prompt_version,
        provider_response_id=proposal.provider_response_id,
        created_at=proposal.created_at,
        created_by=proposal.created_by,
        evidence=[
            AdminClarificationEvidenceResponse(
                evidence_id=item.evidence_key,
                source_id=item.source_revision.source_document.source_id,
                source_revision_id=item.source_revision.revision_id,
                source_title=item.source_revision.source_document.title,
                official_url=item.source_revision.source_document.official_url,
                locator=item.locator,
                excerpt=item.excerpt,
                relation=item.relation,
                explanation=item.explanation,
            )
            for item in sorted(proposal.evidence, key=lambda value: value.evidence_key)
        ],
    )


def source_format(mime_type: str) -> str:
    return "pdf" if mime_type == "application/pdf" else "html"


def _normalization_summary(
    normalization: SourceNormalization | None,
) -> AdminSourceNormalizationSummaryResponse | None:
    if normalization is None:
        return None
    fields = [
        field
        for candidate in normalization.measure_candidates
        for field in candidate.fields
    ]
    return AdminSourceNormalizationSummaryResponse(
        normalization_id=normalization.normalization_id,
        status=normalization.status,
        parser_version=normalization.parser_version,
        measure_candidate_count=len(normalization.measure_candidates),
        staged_field_count=sum(
            field.staging_status
            in {NormalizedStagingStatus.STAGED, NormalizedStagingStatus.EXISTING}
            for field in fields
        ),
        created_at=normalization.created_at,
        created_by=normalization.created_by,
    )


def _extraction_response(
    extraction: SourceExtraction | None,
) -> AdminSourceExtractionResponse | None:
    if extraction is None:
        return None
    latest_normalization = max(
        extraction.normalizations, key=lambda item: item.created_at, default=None
    )
    return AdminSourceExtractionResponse(
        extraction_id=extraction.extraction_id,
        sequence=extraction.sequence,
        status=extraction.status,
        page_count=extraction.page_count,
        segment_count=len(extraction.segments),
        error=extraction.error,
        extractor_version=extraction.extractor_version,
        forced=extraction.forced,
        extracted_at=extraction.extracted_at,
        created_by=extraction.created_by,
        normalization=_normalization_summary(latest_normalization),
    )


def _revision_response(revision: SourceRevision) -> AdminSourceRevisionResponse:
    latest_extraction = max(revision.extractions, key=lambda item: item.sequence, default=None)
    return AdminSourceRevisionResponse(
        revision_id=revision.revision_id,
        revision_number=revision.revision_number,
        content_hash=revision.content_hash,
        source_url=revision.source_url,
        final_url=revision.final_url,
        http_status=revision.http_status,
        mime_type=revision.retrieved_mime_type,
        byte_length=revision.byte_length,
        publication_date=revision.publication_date,
        retrieved_at=revision.retrieved_at,
        last_source_check_at=revision.last_source_check_at,
        extraction=_extraction_response(latest_extraction),
    )


def _check_response(check: SourceCheck) -> AdminSourceCheckResponse:
    return AdminSourceCheckResponse(
        check_id=check.check_id,
        outcome=check.outcome,
        checked_at=check.checked_at,
        requested_url=check.requested_url,
        final_url=check.final_url,
        http_status=check.http_status,
        mime_type=check.mime_type,
        byte_length=check.byte_length,
        content_hash=check.content_hash,
        error=check.error,
        forced=check.forced,
        checked_by=check.checked_by,
        revision_id=check.source_revision.revision_id if check.source_revision else None,
        extraction_id=check.extraction.extraction_id if check.extraction else None,
    )


def _source_query():
    return select(SourceDocument).options(
        selectinload(SourceDocument.revisions)
        .selectinload(SourceRevision.extractions)
        .selectinload(SourceExtraction.segments),
        selectinload(SourceDocument.revisions)
        .selectinload(SourceRevision.extractions)
        .selectinload(SourceExtraction.normalizations)
        .selectinload(SourceNormalization.measure_candidates)
        .selectinload(NormalizedMeasureCandidate.fields)
        .selectinload(NormalizedFieldCandidate.staged_field_candidate),
        selectinload(SourceDocument.checks).selectinload(SourceCheck.source_revision),
        selectinload(SourceDocument.checks).selectinload(SourceCheck.extraction),
    )


def _summary(source: SourceDocument) -> AdminSourceSummaryResponse:
    latest_revision = max(
        source.revisions, key=lambda item: item.revision_number, default=None
    )
    latest_check = max(source.checks, key=lambda item: item.checked_at, default=None)
    return AdminSourceSummaryResponse(
        source_id=source.source_id,
        title=source.title,
        official_url=source.official_url,
        source_format=source_format(source.mime_type),
        is_active=source.is_active,
        notes=source.notes,
        created_by=source.created_by,
        created_at=source.created_at,
        updated_at=source.updated_at,
        deactivated_at=source.deactivated_at,
        revision_count=len(source.revisions),
        latest_revision=_revision_response(latest_revision) if latest_revision else None,
        latest_check=_check_response(latest_check) if latest_check else None,
    )


def list_sources(session: Session) -> AdminSourceListResponse:
    sources = list(session.scalars(_source_query().order_by(SourceDocument.source_id)).unique())
    return AdminSourceListResponse(items=[_summary(source) for source in sources])


def get_source_model(session: Session, source_id: str) -> SourceDocument | None:
    return session.scalar(
        _source_query().where(SourceDocument.source_id == source_id)
    )


def source_detail(source: SourceDocument) -> AdminSourceDetailResponse:
    summary = _summary(source)
    return AdminSourceDetailResponse(
        **summary.model_dump(),
        revisions=[
            _revision_response(revision)
            for revision in sorted(
                source.revisions, key=lambda item: item.revision_number, reverse=True
            )
        ],
        checks=[
            _check_response(check)
            for check in sorted(source.checks, key=lambda item: item.checked_at, reverse=True)
        ],
    )


def get_extraction_detail(
    session: Session, extraction_id: str
) -> AdminSourceExtractionDetailResponse | None:
    extraction = session.scalar(
        select(SourceExtraction)
        .where(SourceExtraction.extraction_id == extraction_id)
        .options(
            selectinload(SourceExtraction.segments),
            selectinload(SourceExtraction.normalizations)
            .selectinload(SourceNormalization.measure_candidates)
            .selectinload(NormalizedMeasureCandidate.fields)
            .selectinload(NormalizedFieldCandidate.staged_field_candidate),
            selectinload(SourceExtraction.source_revision).selectinload(
                SourceRevision.source_document
            ),
        )
    )
    if extraction is None:
        return None
    summary = _extraction_response(extraction)
    if summary is None:  # pragma: no cover - narrowed by the query above
        return None
    return AdminSourceExtractionDetailResponse(
        **summary.model_dump(),
        source_id=extraction.source_revision.source_document.source_id,
        revision_id=extraction.source_revision.revision_id,
        segments=[
            AdminSourceSegmentResponse(
                sequence=segment.sequence,
                locator=segment.locator,
                text=segment.text,
            )
            for segment in sorted(extraction.segments, key=lambda item: item.sequence)
        ],
    )


def get_extraction_model(session: Session, extraction_id: str) -> SourceExtraction | None:
    return session.scalar(
        select(SourceExtraction)
        .where(SourceExtraction.extraction_id == extraction_id)
        .options(
            selectinload(SourceExtraction.segments),
            selectinload(SourceExtraction.source_revision).selectinload(
                SourceRevision.source_document
            ),
            selectinload(SourceExtraction.normalizations)
            .selectinload(SourceNormalization.measure_candidates)
            .selectinload(NormalizedMeasureCandidate.fields)
            .selectinload(NormalizedFieldCandidate.staged_field_candidate),
            selectinload(SourceExtraction.normalizations)
            .selectinload(SourceNormalization.measure_candidates)
            .selectinload(NormalizedMeasureCandidate.fields)
            .selectinload(NormalizedFieldCandidate.source_text_segment),
            selectinload(SourceExtraction.normalizations)
            .selectinload(SourceNormalization.measure_candidates)
            .selectinload(NormalizedMeasureCandidate.matched_measure_version),
        )
    )


def normalization_detail(
    normalization: SourceNormalization,
) -> AdminSourceNormalizationDetailResponse:
    summary = _normalization_summary(normalization)
    if summary is None:  # pragma: no cover - narrowed by the argument
        raise ValueError("Normalization is required.")
    extraction = normalization.source_extraction
    return AdminSourceNormalizationDetailResponse(
        **summary.model_dump(),
        extraction_id=extraction.extraction_id,
        source_id=extraction.source_revision.source_document.source_id,
        revision_id=extraction.source_revision.revision_id,
        candidates=[
            AdminNormalizedMeasureCandidateResponse(
                candidate_id=candidate.candidate_id,
                sequence=candidate.sequence,
                identity_status=candidate.identity_status,
                measure_id_candidate=candidate.measure_id_candidate,
                performance_year_candidate=candidate.performance_year_candidate,
                collection_type_candidate=candidate.collection_type_candidate,
                specification_identifier_candidate=(
                    candidate.specification_identifier_candidate
                ),
                matched_version_id=(
                    candidate.matched_measure_version.version_id
                    if candidate.matched_measure_version
                    else None
                ),
                issues=candidate.issues.splitlines() if candidate.issues else [],
                fields=[
                    AdminNormalizedFieldResponse(
                        field_candidate_id=field.field_candidate_id,
                        field_name=field.field_name,
                        candidate_value=field.candidate_value,
                        status=field.status,
                        segment_sequence=(
                            field.source_text_segment.sequence
                            if field.source_text_segment
                            else None
                        ),
                        evidence_locator=field.evidence_locator,
                        source_excerpt=field.source_excerpt,
                        staging_status=field.staging_status,
                        staged_review_item_id=(
                            field.staged_field_candidate.review_item_id
                            if field.staged_field_candidate
                            else None
                        ),
                        clarifications=[
                            clarification_response(proposal)
                            for proposal in sorted(
                                field.clarifications,
                                key=lambda item: item.created_at,
                                reverse=True,
                            )
                        ],
                    )
                    for field in sorted(candidate.fields, key=lambda item: item.field_name)
                ],
            )
            for candidate in sorted(
                normalization.measure_candidates, key=lambda item: item.sequence
            )
        ],
    )


def get_normalization_model(
    session: Session, normalization_id: str
) -> SourceNormalization | None:
    return session.scalar(
        select(SourceNormalization)
        .where(SourceNormalization.normalization_id == normalization_id)
        .options(
            selectinload(SourceNormalization.source_extraction)
            .selectinload(SourceExtraction.source_revision)
            .selectinload(SourceRevision.source_document),
            selectinload(SourceNormalization.measure_candidates).selectinload(
                NormalizedMeasureCandidate.matched_measure_version
            ),
            selectinload(SourceNormalization.measure_candidates)
            .selectinload(NormalizedMeasureCandidate.fields)
            .selectinload(NormalizedFieldCandidate.source_text_segment),
            selectinload(SourceNormalization.measure_candidates)
            .selectinload(NormalizedMeasureCandidate.fields)
            .selectinload(NormalizedFieldCandidate.staged_field_candidate),
            selectinload(SourceNormalization.measure_candidates)
            .selectinload(NormalizedMeasureCandidate.fields)
            .selectinload(NormalizedFieldCandidate.clarifications)
            .selectinload(AIClarificationProposal.evidence)
            .selectinload(AIClarificationEvidence.source_revision)
            .selectinload(SourceRevision.source_document),
        )
    )
