from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.domain import (
    AffectedField,
    CandidateReviewDecision,
    ChangeStatus,
    CollectionType,
    FieldAvailability,
    FieldPublicationEligibility,
    PublicationState,
    PublicVerificationStatus,
    SourceCheckOutcome,
    SourceExtractionStatus,
)


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


class PublicMeasurePage(BaseModel):
    items: list[PublicMeasureSummary]
    pagination: PaginationMeta


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


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
