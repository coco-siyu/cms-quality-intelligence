from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from app.domain import (
    AffectedField,
    CandidateReviewDecision,
    ChangeEvidenceSide,
    ChangeStatus,
    ClarificationEvidenceRelation,
    ClarificationOutcome,
    CollectionType,
    ComparisonEvidenceStatus,
    ComparisonPublicationEligibility,
    ComparisonReviewDecision,
    FieldAvailability,
    FieldPublicationEligibility,
    ImpactExplanationReviewDecision,
    IngestionItemStage,
    IngestionRunStatus,
    NormalizedFieldStatus,
    NormalizedIdentityStatus,
    NormalizedStagingStatus,
    PublicationState,
    PublicVerificationStatus,
    ReviewRole,
    SourceCheckOutcome,
    SourceExtractionStatus,
    SourceNormalizationStatus,
    TaskProposalStatus,
)
from app.services.impact_explanation import ImpactExplanationOutput


class HealthResponse(BaseModel):
    status: Literal["ok"]


class ApiError(BaseModel):
    code: str
    message: str
    details: list[dict[str, Any]] = Field(default_factory=list)


class PerformanceYearList(BaseModel):
    years: list[int]
    default_from_year: int
    default_to_year: int


class EvidenceReferenceResponse(BaseModel):
    evidence_id: str
    source_revision_id: str
    document_title: str
    official_url: HttpUrl
    publication_date: date | None
    effective_date: date | None
    locator: str | None
    excerpt: str


class FreshnessResponse(BaseModel):
    last_verified_at: datetime | None
    last_source_check_at: datetime
    verification_status: PublicVerificationStatus
    newer_revision_detected: bool


class SpecificationFieldResponse(BaseModel):
    field: AffectedField
    availability: FieldAvailability
    value: str | None
    evidence: list[EvidenceReferenceResponse]


class ChangeFieldEvidenceResponse(EvidenceReferenceResponse):
    side: ChangeEvidenceSide


class ChangeFieldResponse(BaseModel):
    field: AffectedField
    status: ChangeStatus
    from_availability: FieldAvailability
    to_availability: FieldAvailability
    from_value: str | None
    to_value: str | None
    evidence: list[ChangeFieldEvidenceResponse]


class PublicChangeRecord(BaseModel):
    measure_id: str
    measure_name: str
    program: str
    collection_type: CollectionType
    from_year: int
    to_year: int
    status: ChangeStatus
    evidence_status: ComparisonEvidenceStatus
    approved_at: datetime
    published_at: datetime
    fields: list[ChangeFieldResponse]


class PublicImpactExplanation(BaseModel):
    measure_id: str
    measure_name: str
    program: str
    collection_type: CollectionType
    from_year: int
    to_year: int
    approved_at: datetime
    published_at: datetime
    output: ImpactExplanationOutput
    evidence: list[ChangeFieldEvidenceResponse]


class MeasureVersionResponse(BaseModel):
    version_id: str
    performance_year: int
    program: str
    is_program_member: bool
    fields: list[SpecificationFieldResponse]


class PublicMeasureSummary(BaseModel):
    measure_id: str
    name: str
    description: str
    performance_years: list[int]
    change_status: ChangeStatus
    affected_fields: list[AffectedField]
    freshness: FreshnessResponse


class PublicMeasureDetail(PublicMeasureSummary):
    versions: list[MeasureVersionResponse]


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int


class PublicChangePage(BaseModel):
    items: list[PublicChangeRecord]
    pagination: PaginationMeta


class AdminComparisonReviewResponse(BaseModel):
    decision: ComparisonReviewDecision
    reviewer_name: str
    reviewed_at: datetime
    reviewer_notes: str | None


class AdminComparisonResponse(BaseModel):
    comparison_id: int
    measure_id: str
    measure_name: str
    program: str
    collection_type: CollectionType
    from_year: int
    to_year: int
    status: ChangeStatus
    evidence_status: ComparisonEvidenceStatus
    publication_state: PublicationState
    publication_eligibility: ComparisonPublicationEligibility
    publication_blocker: str | None
    review_decision: ComparisonReviewDecision
    reviewed_at: datetime | None
    reviewer_name: str | None
    reviewer_notes: str | None
    published_at: datetime | None
    published_by: str | None
    created_at: datetime
    fields: list[ChangeFieldResponse]
    review_history: list[AdminComparisonReviewResponse]


class AdminComparisonPage(BaseModel):
    items: list[AdminComparisonResponse]


class AdminImpactExplanationDraftResponse(BaseModel):
    draft_id: str
    comparison_id: int
    provider: str
    model: str
    prompt_version: str
    input_digest: str
    generation_sequence: int = Field(ge=1)
    output: ImpactExplanationOutput
    review_decision: ImpactExplanationReviewDecision
    approved_output: ImpactExplanationOutput | None
    reviewed_at: datetime | None
    reviewed_by: str | None
    publication_state: PublicationState
    published_at: datetime | None
    published_by: str | None
    outdated_at: datetime | None
    cited_evidence_ids: list[str]
    provider_response_id: str | None
    created_at: datetime
    created_by: str


class AdminImpactExplanationDraftPage(BaseModel):
    items: list[AdminImpactExplanationDraftResponse]


class AdminImpactTaskProposalResponse(BaseModel):
    proposal_id: str
    review_id: str
    impact_explanation_draft_id: str
    sequence: int = Field(ge=1)
    role: ReviewRole
    title: str
    description: str | None
    status: TaskProposalStatus
    evidence: list[ChangeFieldEvidenceResponse]
    provider: str
    model: str
    prompt_version: str
    input_digest: str
    provider_response_id: str | None
    decided_at: datetime | None
    decided_by: str | None
    created_at: datetime
    created_by: str


class AdminImpactTaskProposalPage(BaseModel):
    items: list[AdminImpactTaskProposalResponse]


class AdminImpactExplanationReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["approve", "reject"]
    output: ImpactExplanationOutput | None = None

    @model_validator(mode="after")
    def require_decision_output(self) -> "AdminImpactExplanationReviewRequest":
        if self.decision == "approve" and self.output is None:
            raise ValueError("Approval requires the complete reviewed explanation pair.")
        if self.decision == "reject" and self.output is not None:
            raise ValueError("Rejected drafts cannot include approved wording.")
        return self


class AdminComparisonGenerationRequest(BaseModel):
    from_year: int = Field(ge=2000, le=2100)
    to_year: int = Field(ge=2000, le=2100)
    collection_type: Literal["program_roster"] = "program_roster"


class AdminComparisonGenerationResponse(BaseModel):
    prepared: int
    existing: int
    skipped_measure_ids: list[str]


class AdminComparisonDecisionRequest(BaseModel):
    decision: Literal["approve", "needs_revision"]
    reviewer_notes: str | None = Field(default=None, max_length=4_000)


class PublicMeasurePage(BaseModel):
    items: list[PublicMeasureSummary]
    pagination: PaginationMeta


class PublicMeasureNavigation(BaseModel):
    measure_id: str
    position: int
    total_items: int
    previous_measure_id: str | None
    next_measure_id: str | None


class MeasureVersionList(BaseModel):
    measure_id: str
    versions: list[MeasureVersionResponse]


class AdminLoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=1, max_length=1000)


class AdminSessionResponse(BaseModel):
    configured: bool
    authenticated: bool
    username: str | None


class AdminReviewSummary(BaseModel):
    private_measures: int
    draft_versions: int
    pending_candidates: int
    decided_candidates: int
    source_revisions: int
    newer_revision_flags: int


class AdminMeasureSummary(BaseModel):
    measure_id: str
    name: str
    description: str
    performance_years: list[int]
    draft_versions: int
    pending_candidates: int
    decided_candidates: int
    source_documents: int
    newer_revision_detected: bool
    last_source_check_at: datetime | None


class AdminMeasurePage(BaseModel):
    items: list[AdminMeasureSummary]
    pagination: PaginationMeta


class AdminMembershipResponse(BaseModel):
    performance_year: int
    program: str
    is_program_member: bool
    publication_state: PublicationState
    verified_at: datetime | None


class AdminCandidateReviewResponse(BaseModel):
    decision: CandidateReviewDecision
    reviewed_value: str | None
    reviewer_name: str
    reviewed_at: datetime
    reviewer_notes: str | None


class AdminFieldCandidateResponse(BaseModel):
    review_item_id: str
    field_name: str
    candidate_value: str
    source_excerpt: str | None
    extraction_status: str
    evidence_locator: str
    review_decision: CandidateReviewDecision
    reviewed_value: str | None
    reviewer_name: str | None
    reviewed_at: datetime | None
    reviewer_notes: str | None
    publication_state: PublicationState
    publication_eligibility: FieldPublicationEligibility
    publication_blocker: str | None
    published_field: AffectedField | None
    published_at: datetime | None
    published_by: str | None
    source_id: str
    source_revision_id: str
    source_title: str
    official_url: HttpUrl
    source_content_hash: str
    review_history: list[AdminCandidateReviewResponse]


class AdminCandidateDecisionRequest(BaseModel):
    decision: Literal["approve", "needs_revision", "not_applicable"]
    reviewed_value: str | None = Field(default=None, max_length=20_000)
    reviewer_notes: str | None = Field(default=None, max_length=4_000)


class AdminMeasureVersionResponse(BaseModel):
    version_id: str
    performance_year: int
    program: str
    collection_type: CollectionType
    specification_identifier: str | None
    publication_state: PublicationState
    verification_status: PublicVerificationStatus
    newer_revision_detected: bool
    last_source_check_at: datetime
    candidates: list[AdminFieldCandidateResponse]


class AdminMeasureDetail(BaseModel):
    measure_id: str
    name: str
    description: str
    is_public: bool
    memberships: list[AdminMembershipResponse]
    versions: list[AdminMeasureVersionResponse]


class AdminSourceCreateRequest(BaseModel):
    source_id: str = Field(pattern=r"^[A-Z0-9][A-Z0-9_-]{2,99}$")
    title: str = Field(min_length=3, max_length=500)
    official_url: HttpUrl
    source_format: Literal["html", "pdf"]
    notes: str | None = Field(default=None, max_length=4_000)


class AdminSourceUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=500)
    official_url: HttpUrl | None = None
    source_format: Literal["html", "pdf"] | None = None
    notes: str | None = Field(default=None, max_length=4_000)
    is_active: bool | None = None


class AdminSourceNormalizationSummaryResponse(BaseModel):
    normalization_id: str
    status: SourceNormalizationStatus
    parser_version: str
    measure_candidate_count: int
    staged_field_count: int
    created_at: datetime
    created_by: str


class AdminClarificationEvidenceResponse(BaseModel):
    evidence_id: str
    source_id: str
    source_revision_id: str
    source_title: str
    official_url: HttpUrl
    locator: str
    excerpt: str
    relation: ClarificationEvidenceRelation
    explanation: str


class AdminClarificationProposalResponse(BaseModel):
    clarification_id: str
    field_candidate_id: str
    outcome: ClarificationOutcome
    proposed_value: str | None
    summary: str
    provider: str
    model: str
    prompt_version: str
    provider_response_id: str | None
    created_at: datetime
    created_by: str
    evidence: list[AdminClarificationEvidenceResponse]


class AdminNormalizedFieldResponse(BaseModel):
    field_candidate_id: str
    field_name: str
    candidate_value: str | None
    status: NormalizedFieldStatus
    segment_sequence: int | None
    evidence_locator: str | None
    source_excerpt: str | None
    staging_status: NormalizedStagingStatus
    staged_review_item_id: str | None
    clarifications: list[AdminClarificationProposalResponse]


class AdminNormalizedMeasureCandidateResponse(BaseModel):
    candidate_id: str
    sequence: int
    identity_status: NormalizedIdentityStatus
    measure_id_candidate: str | None
    performance_year_candidate: int | None
    collection_type_candidate: CollectionType | None
    specification_identifier_candidate: str | None
    matched_version_id: str | None
    issues: list[str]
    fields: list[AdminNormalizedFieldResponse]


class AdminSourceNormalizationDetailResponse(AdminSourceNormalizationSummaryResponse):
    extraction_id: str
    source_id: str
    revision_id: str
    candidates: list[AdminNormalizedMeasureCandidateResponse]


class AdminSourceExtractionResponse(BaseModel):
    extraction_id: str
    sequence: int
    status: SourceExtractionStatus
    page_count: int | None
    segment_count: int
    error: str | None
    extractor_version: str
    forced: bool
    extracted_at: datetime
    created_by: str
    normalization: AdminSourceNormalizationSummaryResponse | None


class AdminSourceRevisionResponse(BaseModel):
    revision_id: str
    revision_number: int
    content_hash: str
    source_url: HttpUrl | None
    final_url: HttpUrl | None
    http_status: int | None
    mime_type: str | None
    byte_length: int | None
    publication_date: date | None
    retrieved_at: datetime
    last_source_check_at: datetime
    extraction: AdminSourceExtractionResponse | None


class AdminSourceCheckResponse(BaseModel):
    check_id: str
    outcome: SourceCheckOutcome
    checked_at: datetime
    requested_url: HttpUrl
    final_url: HttpUrl | None
    http_status: int | None
    mime_type: str | None
    byte_length: int | None
    content_hash: str | None
    error: str | None
    forced: bool
    checked_by: str
    revision_id: str | None
    extraction_id: str | None


class AdminSourceSummaryResponse(BaseModel):
    source_id: str
    title: str
    official_url: HttpUrl
    source_format: Literal["html", "pdf"]
    is_active: bool
    notes: str | None
    created_by: str | None
    created_at: datetime
    updated_at: datetime
    deactivated_at: datetime | None
    revision_count: int
    latest_revision: AdminSourceRevisionResponse | None
    latest_check: AdminSourceCheckResponse | None


class AdminSourceListResponse(BaseModel):
    items: list[AdminSourceSummaryResponse]


class AdminSourceDetailResponse(AdminSourceSummaryResponse):
    revisions: list[AdminSourceRevisionResponse]
    checks: list[AdminSourceCheckResponse]


class AdminSourceCheckRequest(BaseModel):
    force: bool = False


class AdminSourceSegmentResponse(BaseModel):
    sequence: int
    locator: str
    text: str


class AdminSourceExtractionDetailResponse(AdminSourceExtractionResponse):
    source_id: str
    revision_id: str
    segments: list[AdminSourceSegmentResponse]


class AdminIngestionEventResponse(BaseModel):
    event_id: str
    stage: IngestionItemStage
    occurred_at: datetime
    detail: str | None


class AdminIngestionItemResponse(BaseModel):
    item_id: str
    sequence: int
    source_id: str
    source_title: str
    stage: IngestionItemStage
    source_check_id: str | None
    source_check_outcome: SourceCheckOutcome | None
    started_at: datetime | None
    completed_at: datetime | None
    error: str | None
    events: list[AdminIngestionEventResponse]


class AdminIngestionRunResponse(BaseModel):
    run_id: str
    status: IngestionRunStatus
    source_count: int
    completed_count: int
    failed_count: int
    started_at: datetime
    completed_at: datetime | None
    created_by: str
    items: list[AdminIngestionItemResponse]


class AdminIngestionRunListResponse(BaseModel):
    items: list[AdminIngestionRunResponse]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
