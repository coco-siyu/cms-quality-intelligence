from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.domain import (
    AffectedField,
    ChangeStatus,
    FieldAvailability,
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


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
