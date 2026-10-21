from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.domain import (
    AffectedField,
    CandidateReviewDecision,
    ChangeStatus,
    CollectionType,
    FieldAvailability,
    PublicationState,
    PublicVerificationStatus,
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


class AdminFieldCandidateResponse(BaseModel):
    review_item_id: str
    field_name: str
    candidate_value: str
    extraction_status: str
    evidence_locator: str
    review_decision: CandidateReviewDecision
    reviewed_value: str | None
    reviewer_name: str | None
    reviewed_at: datetime | None
    reviewer_notes: str | None
    source_id: str
    source_revision_id: str
    source_title: str
    official_url: HttpUrl
    source_content_hash: str


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


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
