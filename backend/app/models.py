from datetime import UTC, date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.domain import (
    AffectedField,
    CandidateReviewDecision,
    ChangeStatus,
    ClarificationEvidenceRelation,
    ClarificationOutcome,
    CollectionType,
    FieldAvailability,
    IngestionItemStage,
    IngestionRunStatus,
    NormalizedFieldStatus,
    NormalizedIdentityStatus,
    NormalizedStagingStatus,
    PublicationState,
    PublicVerificationStatus,
    SourceCheckOutcome,
    SourceExtractionStatus,
    SourceNormalizationStatus,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


publication_state_enum = Enum(
    PublicationState,
    name="publication_state",
    native_enum=False,
    create_constraint=True,
    values_callable=lambda values: [value.value for value in values],
)
verification_status_enum = Enum(
    PublicVerificationStatus,
    name="public_verification_status",
    native_enum=False,
    create_constraint=True,
    values_callable=lambda values: [value.value for value in values],
)
field_availability_enum = Enum(
    FieldAvailability,
    name="field_availability",
    native_enum=False,
    create_constraint=True,
    values_callable=lambda values: [value.value for value in values],
)
affected_field_enum = Enum(
    AffectedField,
    name="affected_field",
    native_enum=False,
    create_constraint=True,
    values_callable=lambda values: [value.value for value in values],
)
change_status_enum = Enum(
    ChangeStatus,
    name="change_status",
    native_enum=False,
    create_constraint=True,
    values_callable=lambda values: [value.value for value in values],
)
collection_type_enum = Enum(
    CollectionType,
    name="collection_type",
    native_enum=False,
    create_constraint=True,
    values_callable=lambda values: [value.value for value in values],
)
candidate_review_decision_enum = Enum(
    CandidateReviewDecision,
    name="candidate_review_decision",
    native_enum=False,
    create_constraint=True,
    values_callable=lambda values: [value.value for value in values],
)
source_check_outcome_enum = Enum(
    SourceCheckOutcome,
    name="source_check_outcome",
    native_enum=False,
    create_constraint=True,
    values_callable=lambda values: [value.value for value in values],
)
source_extraction_status_enum = Enum(
    SourceExtractionStatus,
    name="source_extraction_status",
    native_enum=False,
    create_constraint=True,
    values_callable=lambda values: [value.value for value in values],
)
source_normalization_status_enum = Enum(
    SourceNormalizationStatus,
    name="source_normalization_status",
    native_enum=False,
    create_constraint=True,
    values_callable=lambda values: [value.value for value in values],
)
normalized_identity_status_enum = Enum(
    NormalizedIdentityStatus,
    name="normalized_identity_status",
    native_enum=False,
    create_constraint=True,
    values_callable=lambda values: [value.value for value in values],
)
normalized_field_status_enum = Enum(
    NormalizedFieldStatus,
    name="normalized_field_status",
    native_enum=False,
    create_constraint=True,
    values_callable=lambda values: [value.value for value in values],
)
normalized_staging_status_enum = Enum(
    NormalizedStagingStatus,
    name="normalized_staging_status",
    native_enum=False,
    create_constraint=True,
    values_callable=lambda values: [value.value for value in values],
)
clarification_outcome_enum = Enum(
    ClarificationOutcome,
    name="clarification_outcome",
    native_enum=False,
    create_constraint=True,
    values_callable=lambda values: [value.value for value in values],
)
clarification_evidence_relation_enum = Enum(
    ClarificationEvidenceRelation,
    name="clarification_evidence_relation",
    native_enum=False,
    create_constraint=True,
    values_callable=lambda values: [value.value for value in values],
)
ingestion_run_status_enum = Enum(
    IngestionRunStatus,
    name="ingestion_run_status",
    native_enum=False,
    create_constraint=True,
    values_callable=lambda values: [value.value for value in values],
)
ingestion_item_stage_enum = Enum(
    IngestionItemStage,
    name="ingestion_item_stage",
    native_enum=False,
    create_constraint=True,
    values_callable=lambda values: [value.value for value in values],
)


class Measure(Base):
    __tablename__ = "measures"

    id: Mapped[int] = mapped_column(primary_key=True)
    measure_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    memberships: Mapped[list["ProgramMembership"]] = relationship(
        back_populates="measure", cascade="all, delete-orphan"
    )
    versions: Mapped[list["MeasureVersion"]] = relationship(
        back_populates="measure", cascade="all, delete-orphan"
    )
    comparisons: Mapped[list["MeasureComparison"]] = relationship(
        back_populates="measure", cascade="all, delete-orphan"
    )


class ProgramMembership(Base):
    __tablename__ = "program_memberships"
    __table_args__ = (
        UniqueConstraint("measure_id", "program", "performance_year"),
        CheckConstraint("performance_year >= 2000 AND performance_year <= 2100"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    measure_id: Mapped[int] = mapped_column(ForeignKey("measures.id", ondelete="CASCADE"))
    program: Mapped[str] = mapped_column(String(120))
    performance_year: Mapped[int] = mapped_column(Integer, index=True)
    is_program_member: Mapped[bool] = mapped_column(Boolean)
    publication_state: Mapped[PublicationState] = mapped_column(
        publication_state_enum, default=PublicationState.DRAFT, index=True
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    measure: Mapped[Measure] = relationship(back_populates="memberships")


class SourceDocument(Base):
    __tablename__ = "source_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(500))
    official_url: Mapped[str] = mapped_column(Text, unique=True)
    mime_type: Mapped[str] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    revisions: Mapped[list["SourceRevision"]] = relationship(
        back_populates="source_document", cascade="all, delete-orphan"
    )
    checks: Mapped[list["SourceCheck"]] = relationship(
        back_populates="source_document", cascade="all, delete-orphan"
    )
    ingestion_items: Mapped[list["IngestionRunItem"]] = relationship(
        back_populates="source_document"
    )


class SourceRevision(Base):
    __tablename__ = "source_revisions"
    __table_args__ = (
        UniqueConstraint("source_document_id", "revision_number"),
        UniqueConstraint("source_document_id", "content_hash"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    revision_id: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    source_document_id: Mapped[int] = mapped_column(
        ForeignKey("source_documents.id", ondelete="RESTRICT")
    )
    revision_number: Mapped[int] = mapped_column(Integer)
    content_hash: Mapped[str] = mapped_column(String(128))
    publication_date: Mapped[date | None] = mapped_column(Date)
    effective_date: Mapped[date | None] = mapped_column(Date)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_source_check_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_url: Mapped[str | None] = mapped_column(Text)
    final_url: Mapped[str | None] = mapped_column(Text)
    http_status: Mapped[int | None] = mapped_column(Integer)
    retrieved_mime_type: Mapped[str | None] = mapped_column(String(120))
    byte_length: Mapped[int | None] = mapped_column(Integer)
    content_blob: Mapped[bytes | None] = mapped_column(LargeBinary)
    publication_state: Mapped[PublicationState] = mapped_column(
        publication_state_enum, default=PublicationState.DRAFT, index=True
    )
    verification_status: Mapped[PublicVerificationStatus] = mapped_column(
        verification_status_enum, default=PublicVerificationStatus.PARTIALLY_VERIFIED
    )

    source_document: Mapped[SourceDocument] = relationship(back_populates="revisions")
    evidence_references: Mapped[list["EvidenceReference"]] = relationship(
        back_populates="source_revision"
    )
    field_candidates: Mapped[list["SpecificationFieldCandidate"]] = relationship(
        back_populates="source_revision"
    )
    extractions: Mapped[list["SourceExtraction"]] = relationship(
        back_populates="source_revision", cascade="all, delete-orphan"
    )
    checks: Mapped[list["SourceCheck"]] = relationship(back_populates="source_revision")


class SourceExtraction(Base):
    __tablename__ = "source_extractions"
    __table_args__ = (
        UniqueConstraint("source_revision_id", "sequence"),
        CheckConstraint("sequence >= 1"),
        CheckConstraint("page_count IS NULL OR page_count >= 0"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    extraction_id: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    source_revision_id: Mapped[int] = mapped_column(
        ForeignKey("source_revisions.id", ondelete="RESTRICT")
    )
    sequence: Mapped[int] = mapped_column(Integer)
    status: Mapped[SourceExtractionStatus] = mapped_column(
        source_extraction_status_enum, index=True
    )
    page_count: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)
    extractor_version: Mapped[str] = mapped_column(String(120))
    forced: Mapped[bool] = mapped_column(Boolean, default=False)
    extracted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    created_by: Mapped[str] = mapped_column(String(200))

    source_revision: Mapped[SourceRevision] = relationship(back_populates="extractions")
    segments: Mapped[list["SourceTextSegment"]] = relationship(
        back_populates="extraction", cascade="all, delete-orphan"
    )
    checks: Mapped[list["SourceCheck"]] = relationship(back_populates="extraction")
    normalizations: Mapped[list["SourceNormalization"]] = relationship(
        back_populates="source_extraction", cascade="all, delete-orphan"
    )


class SourceTextSegment(Base):
    __tablename__ = "source_text_segments"
    __table_args__ = (UniqueConstraint("source_extraction_id", "sequence"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_extraction_id: Mapped[int] = mapped_column(
        ForeignKey("source_extractions.id", ondelete="CASCADE")
    )
    sequence: Mapped[int] = mapped_column(Integer)
    locator: Mapped[str] = mapped_column(String(500))
    text: Mapped[str] = mapped_column(Text)

    extraction: Mapped[SourceExtraction] = relationship(back_populates="segments")
    normalized_fields: Mapped[list["NormalizedFieldCandidate"]] = relationship(
        back_populates="source_text_segment"
    )
    clarification_evidence: Mapped[list["AIClarificationEvidence"]] = relationship(
        back_populates="source_text_segment"
    )


class SourceNormalization(Base):
    __tablename__ = "source_normalizations"
    __table_args__ = (UniqueConstraint("source_extraction_id", "parser_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    normalization_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    source_extraction_id: Mapped[int] = mapped_column(
        ForeignKey("source_extractions.id", ondelete="RESTRICT")
    )
    parser_version: Mapped[str] = mapped_column(String(120))
    status: Mapped[SourceNormalizationStatus] = mapped_column(
        source_normalization_status_enum, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    created_by: Mapped[str] = mapped_column(String(200))

    source_extraction: Mapped[SourceExtraction] = relationship(
        back_populates="normalizations"
    )
    measure_candidates: Mapped[list["NormalizedMeasureCandidate"]] = relationship(
        back_populates="normalization", cascade="all, delete-orphan"
    )


class NormalizedMeasureCandidate(Base):
    __tablename__ = "normalized_measure_candidates"
    __table_args__ = (
        UniqueConstraint("source_normalization_id", "sequence"),
        CheckConstraint("sequence >= 1"),
        CheckConstraint(
            "performance_year_candidate IS NULL OR "
            "(performance_year_candidate >= 2000 AND performance_year_candidate <= 2100)"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    source_normalization_id: Mapped[int] = mapped_column(
        ForeignKey("source_normalizations.id", ondelete="CASCADE")
    )
    sequence: Mapped[int] = mapped_column(Integer)
    identity_status: Mapped[NormalizedIdentityStatus] = mapped_column(
        normalized_identity_status_enum, index=True
    )
    measure_id_candidate: Mapped[str | None] = mapped_column(String(80))
    performance_year_candidate: Mapped[int | None] = mapped_column(Integer)
    collection_type_candidate: Mapped[str | None] = mapped_column(String(80))
    specification_identifier_candidate: Mapped[str | None] = mapped_column(String(120))
    matched_measure_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("measure_versions.id", ondelete="RESTRICT")
    )
    issues: Mapped[str | None] = mapped_column(Text)

    normalization: Mapped[SourceNormalization] = relationship(
        back_populates="measure_candidates"
    )
    matched_measure_version: Mapped["MeasureVersion | None"] = relationship(
        back_populates="normalized_candidates"
    )
    fields: Mapped[list["NormalizedFieldCandidate"]] = relationship(
        back_populates="measure_candidate", cascade="all, delete-orphan"
    )


class NormalizedFieldCandidate(Base):
    __tablename__ = "normalized_field_candidates"
    __table_args__ = (
        UniqueConstraint("normalized_measure_candidate_id", "field_name"),
        CheckConstraint(
            "(status = 'extracted' AND candidate_value IS NOT NULL "
            "AND source_text_segment_id IS NOT NULL AND evidence_locator IS NOT NULL "
            "AND source_excerpt IS NOT NULL) OR "
            "(status = 'unresolved' AND candidate_value IS NULL)",
            name="ck_normalized_field_evidence",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    field_candidate_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    normalized_measure_candidate_id: Mapped[int] = mapped_column(
        ForeignKey("normalized_measure_candidates.id", ondelete="CASCADE")
    )
    field_name: Mapped[str] = mapped_column(String(80))
    candidate_value: Mapped[str | None] = mapped_column(Text)
    status: Mapped[NormalizedFieldStatus] = mapped_column(
        normalized_field_status_enum, index=True
    )
    source_text_segment_id: Mapped[int | None] = mapped_column(
        ForeignKey("source_text_segments.id", ondelete="RESTRICT")
    )
    evidence_locator: Mapped[str | None] = mapped_column(String(1000))
    source_excerpt: Mapped[str | None] = mapped_column(Text)
    staging_status: Mapped[NormalizedStagingStatus] = mapped_column(
        normalized_staging_status_enum, index=True
    )
    staged_field_candidate_id: Mapped[int | None] = mapped_column(
        ForeignKey("specification_field_candidates.id", ondelete="RESTRICT")
    )

    measure_candidate: Mapped[NormalizedMeasureCandidate] = relationship(
        back_populates="fields"
    )
    source_text_segment: Mapped[SourceTextSegment | None] = relationship(
        back_populates="normalized_fields"
    )
    staged_field_candidate: Mapped["SpecificationFieldCandidate | None"] = relationship(
        back_populates="normalized_fields"
    )
    clarifications: Mapped[list["AIClarificationProposal"]] = relationship(
        back_populates="normalized_field_candidate", cascade="all, delete-orphan"
    )


class AIClarificationProposal(Base):
    __tablename__ = "ai_clarification_proposals"
    __table_args__ = (
        UniqueConstraint(
            "normalized_field_candidate_id",
            "provider",
            "model",
            "prompt_version",
            "input_digest",
            name="uq_ai_clarification_input",
        ),
        CheckConstraint(
            "(outcome = 'proposed' AND proposed_value IS NOT NULL) OR "
            "(outcome IN ('unresolved', 'conflict') AND proposed_value IS NULL)",
            name="ck_ai_clarification_proposed_value",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    clarification_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    normalized_field_candidate_id: Mapped[int] = mapped_column(
        ForeignKey("normalized_field_candidates.id", ondelete="RESTRICT")
    )
    provider: Mapped[str] = mapped_column(String(80))
    model: Mapped[str] = mapped_column(String(160))
    prompt_version: Mapped[str] = mapped_column(String(120))
    input_digest: Mapped[str] = mapped_column(String(128))
    outcome: Mapped[ClarificationOutcome] = mapped_column(
        clarification_outcome_enum, index=True
    )
    proposed_value: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    provider_response_id: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    created_by: Mapped[str] = mapped_column(String(200))

    normalized_field_candidate: Mapped[NormalizedFieldCandidate] = relationship(
        back_populates="clarifications"
    )
    evidence: Mapped[list["AIClarificationEvidence"]] = relationship(
        back_populates="clarification", cascade="all, delete-orphan"
    )


class AIClarificationEvidence(Base):
    __tablename__ = "ai_clarification_evidence"
    __table_args__ = (UniqueConstraint("ai_clarification_proposal_id", "evidence_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    evidence_key: Mapped[str] = mapped_column(String(120), index=True)
    ai_clarification_proposal_id: Mapped[int] = mapped_column(
        ForeignKey("ai_clarification_proposals.id", ondelete="CASCADE")
    )
    source_text_segment_id: Mapped[int] = mapped_column(
        ForeignKey("source_text_segments.id", ondelete="RESTRICT")
    )
    source_revision_id: Mapped[int] = mapped_column(
        ForeignKey("source_revisions.id", ondelete="RESTRICT")
    )
    locator: Mapped[str] = mapped_column(String(1000))
    excerpt: Mapped[str] = mapped_column(Text)
    relation: Mapped[ClarificationEvidenceRelation] = mapped_column(
        clarification_evidence_relation_enum
    )
    explanation: Mapped[str] = mapped_column(Text)

    clarification: Mapped[AIClarificationProposal] = relationship(
        back_populates="evidence"
    )
    source_text_segment: Mapped[SourceTextSegment] = relationship(
        back_populates="clarification_evidence"
    )
    source_revision: Mapped[SourceRevision] = relationship()


class SourceCheck(Base):
    __tablename__ = "source_checks"

    id: Mapped[int] = mapped_column(primary_key=True)
    check_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    source_document_id: Mapped[int] = mapped_column(
        ForeignKey("source_documents.id", ondelete="CASCADE")
    )
    source_revision_id: Mapped[int | None] = mapped_column(
        ForeignKey("source_revisions.id", ondelete="RESTRICT")
    )
    extraction_id: Mapped[int | None] = mapped_column(
        ForeignKey("source_extractions.id", ondelete="RESTRICT")
    )
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    outcome: Mapped[SourceCheckOutcome] = mapped_column(source_check_outcome_enum, index=True)
    requested_url: Mapped[str] = mapped_column(Text)
    final_url: Mapped[str | None] = mapped_column(Text)
    http_status: Mapped[int | None] = mapped_column(Integer)
    mime_type: Mapped[str | None] = mapped_column(String(120))
    byte_length: Mapped[int | None] = mapped_column(Integer)
    content_hash: Mapped[str | None] = mapped_column(String(128))
    error: Mapped[str | None] = mapped_column(Text)
    forced: Mapped[bool] = mapped_column(Boolean, default=False)
    checked_by: Mapped[str] = mapped_column(String(200))

    source_document: Mapped[SourceDocument] = relationship(back_populates="checks")
    source_revision: Mapped[SourceRevision | None] = relationship(back_populates="checks")
    extraction: Mapped[SourceExtraction | None] = relationship(back_populates="checks")
    ingestion_items: Mapped[list["IngestionRunItem"]] = relationship(
        back_populates="source_check"
    )


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    status: Mapped[IngestionRunStatus] = mapped_column(
        ingestion_run_status_enum, default=IngestionRunStatus.RUNNING, index=True
    )
    source_count: Mapped[int] = mapped_column(Integer)
    completed_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str] = mapped_column(String(200))

    items: Mapped[list["IngestionRunItem"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class IngestionRunItem(Base):
    __tablename__ = "ingestion_run_items"
    __table_args__ = (
        UniqueConstraint("ingestion_run_id", "sequence"),
        UniqueConstraint("ingestion_run_id", "source_document_id"),
        CheckConstraint("sequence >= 1"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    ingestion_run_id: Mapped[int] = mapped_column(
        ForeignKey("ingestion_runs.id", ondelete="CASCADE")
    )
    source_document_id: Mapped[int] = mapped_column(
        ForeignKey("source_documents.id", ondelete="RESTRICT")
    )
    source_check_id: Mapped[int | None] = mapped_column(
        ForeignKey("source_checks.id", ondelete="RESTRICT")
    )
    sequence: Mapped[int] = mapped_column(Integer)
    stage: Mapped[IngestionItemStage] = mapped_column(
        ingestion_item_stage_enum, default=IngestionItemStage.PENDING, index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)

    run: Mapped[IngestionRun] = relationship(back_populates="items")
    source_document: Mapped[SourceDocument] = relationship(back_populates="ingestion_items")
    source_check: Mapped[SourceCheck | None] = relationship(back_populates="ingestion_items")
    events: Mapped[list["IngestionRunEvent"]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )


class IngestionRunEvent(Base):
    __tablename__ = "ingestion_run_events"
    __table_args__ = (UniqueConstraint("ingestion_run_item_id", "sequence"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    ingestion_run_item_id: Mapped[int] = mapped_column(
        ForeignKey("ingestion_run_items.id", ondelete="CASCADE")
    )
    sequence: Mapped[int] = mapped_column(Integer)
    stage: Mapped[IngestionItemStage] = mapped_column(ingestion_item_stage_enum)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    detail: Mapped[str | None] = mapped_column(Text)

    item: Mapped[IngestionRunItem] = relationship(back_populates="events")


class MeasureVersion(Base):
    __tablename__ = "measure_versions"
    __table_args__ = (
        UniqueConstraint(
            "measure_id",
            "program",
            "performance_year",
            "collection_type",
            "version_number",
            name="uq_measure_version_variant_revision",
        ),
        CheckConstraint("performance_year >= 2000 AND performance_year <= 2100"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    measure_id: Mapped[int] = mapped_column(ForeignKey("measures.id", ondelete="CASCADE"))
    program: Mapped[str] = mapped_column(String(120))
    performance_year: Mapped[int] = mapped_column(Integer, index=True)
    collection_type: Mapped[CollectionType] = mapped_column(
        collection_type_enum, default=CollectionType.PROGRAM_ROSTER, index=True
    )
    specification_identifier: Mapped[str | None] = mapped_column(String(120))
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    is_program_member: Mapped[bool] = mapped_column(Boolean)
    publication_state: Mapped[PublicationState] = mapped_column(
        publication_state_enum, default=PublicationState.DRAFT, index=True
    )
    verification_status: Mapped[PublicVerificationStatus] = mapped_column(
        verification_status_enum, default=PublicVerificationStatus.PARTIALLY_VERIFIED
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_source_check_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    newer_revision_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    measure: Mapped[Measure] = relationship(back_populates="versions")
    fields: Mapped[list["SpecificationField"]] = relationship(
        back_populates="measure_version", cascade="all, delete-orphan"
    )
    field_candidates: Mapped[list["SpecificationFieldCandidate"]] = relationship(
        back_populates="measure_version", cascade="all, delete-orphan"
    )
    normalized_candidates: Mapped[list["NormalizedMeasureCandidate"]] = relationship(
        back_populates="matched_measure_version"
    )


class SpecificationFieldCandidate(Base):
    __tablename__ = "specification_field_candidates"
    __table_args__ = (
        UniqueConstraint("measure_version_id", "field_name"),
        CheckConstraint(
            "(review_decision = 'pending' AND reviewed_at IS NULL) OR "
            "(review_decision != 'pending' AND reviewed_at IS NOT NULL)",
            name="ck_candidate_review_timestamp",
        ),
        CheckConstraint(
            "(publication_state = 'draft' AND published_field_id IS NULL "
            "AND published_at IS NULL AND published_by IS NULL) OR "
            "(publication_state IN ('published', 'withdrawn') "
            "AND published_field_id IS NOT NULL AND published_at IS NOT NULL "
            "AND published_by IS NOT NULL AND review_decision = 'approve')",
            name="ck_candidate_publication_state",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    review_item_id: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    measure_version_id: Mapped[int] = mapped_column(
        ForeignKey("measure_versions.id", ondelete="CASCADE")
    )
    field_name: Mapped[str] = mapped_column(String(80))
    candidate_value: Mapped[str] = mapped_column(Text)
    source_excerpt: Mapped[str | None] = mapped_column(Text)
    extraction_status: Mapped[str] = mapped_column(String(80))
    source_revision_id: Mapped[int] = mapped_column(
        ForeignKey("source_revisions.id", ondelete="RESTRICT")
    )
    evidence_locator: Mapped[str] = mapped_column(String(1000))
    review_decision: Mapped[CandidateReviewDecision] = mapped_column(
        candidate_review_decision_enum,
        default=CandidateReviewDecision.PENDING,
        index=True,
    )
    reviewed_value: Mapped[str | None] = mapped_column(Text)
    reviewer_name: Mapped[str | None] = mapped_column(String(200))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewer_notes: Mapped[str | None] = mapped_column(Text)
    publication_state: Mapped[PublicationState] = mapped_column(
        publication_state_enum, default=PublicationState.DRAFT, index=True
    )
    published_field_id: Mapped[int | None] = mapped_column(
        ForeignKey("specification_fields.id", ondelete="RESTRICT"), unique=True
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_by: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    measure_version: Mapped[MeasureVersion] = relationship(back_populates="field_candidates")
    source_revision: Mapped[SourceRevision] = relationship(back_populates="field_candidates")
    reviews: Mapped[list["SpecificationFieldCandidateReview"]] = relationship(
        back_populates="field_candidate", cascade="all, delete-orphan"
    )
    published_field: Mapped["SpecificationField | None"] = relationship(
        foreign_keys=[published_field_id]
    )
    normalized_fields: Mapped[list["NormalizedFieldCandidate"]] = relationship(
        back_populates="staged_field_candidate"
    )


class SpecificationFieldCandidateReview(Base):
    __tablename__ = "specification_field_candidate_reviews"
    __table_args__ = (
        CheckConstraint(
            "decision != 'pending'",
            name="ck_candidate_review_event_is_decided",
        ),
        CheckConstraint(
            "(decision = 'approve' AND reviewed_value IS NOT NULL) OR "
            "(decision != 'approve' AND reviewed_value IS NULL)",
            name="ck_candidate_review_event_value",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    specification_field_candidate_id: Mapped[int] = mapped_column(
        ForeignKey("specification_field_candidates.id", ondelete="CASCADE")
    )
    decision: Mapped[CandidateReviewDecision] = mapped_column(
        candidate_review_decision_enum, index=True
    )
    reviewed_value: Mapped[str | None] = mapped_column(Text)
    reviewer_name: Mapped[str] = mapped_column(String(200))
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reviewer_notes: Mapped[str | None] = mapped_column(Text)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    field_candidate: Mapped[SpecificationFieldCandidate] = relationship(
        back_populates="reviews"
    )


class SpecificationField(Base):
    __tablename__ = "specification_fields"
    __table_args__ = (
        UniqueConstraint("measure_version_id", "field"),
        CheckConstraint(
            "(availability = 'available' AND value IS NOT NULL) OR "
            "(availability IN ('unavailable', 'unresolved') AND value IS NULL)",
            name="ck_field_availability_value",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    measure_version_id: Mapped[int] = mapped_column(
        ForeignKey("measure_versions.id", ondelete="CASCADE")
    )
    field: Mapped[AffectedField] = mapped_column(affected_field_enum)
    availability: Mapped[FieldAvailability] = mapped_column(field_availability_enum)
    value: Mapped[str | None] = mapped_column(Text)

    measure_version: Mapped[MeasureVersion] = relationship(back_populates="fields")
    evidence: Mapped[list["EvidenceReference"]] = relationship(
        back_populates="specification_field", cascade="all, delete-orphan"
    )


class EvidenceReference(Base):
    __tablename__ = "evidence_references"

    id: Mapped[int] = mapped_column(primary_key=True)
    evidence_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    specification_field_id: Mapped[int] = mapped_column(
        ForeignKey("specification_fields.id", ondelete="CASCADE")
    )
    source_revision_id: Mapped[int] = mapped_column(
        ForeignKey("source_revisions.id", ondelete="RESTRICT")
    )
    locator: Mapped[str | None] = mapped_column(String(500))
    excerpt: Mapped[str] = mapped_column(Text)

    specification_field: Mapped[SpecificationField] = relationship(back_populates="evidence")
    source_revision: Mapped[SourceRevision] = relationship(back_populates="evidence_references")


class MeasureComparison(Base):
    __tablename__ = "measure_comparisons"
    __table_args__ = (
        UniqueConstraint("measure_id", "program", "from_year", "to_year"),
        CheckConstraint("from_year >= 2000 AND from_year <= 2100"),
        CheckConstraint("to_year >= 2000 AND to_year <= 2100"),
        Index("ix_comparison_year_pair", "from_year", "to_year"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    measure_id: Mapped[int] = mapped_column(ForeignKey("measures.id", ondelete="CASCADE"))
    program: Mapped[str] = mapped_column(String(120))
    from_year: Mapped[int] = mapped_column(Integer)
    to_year: Mapped[int] = mapped_column(Integer)
    status: Mapped[ChangeStatus] = mapped_column(
        change_status_enum, default=ChangeStatus.UNKNOWN, index=True
    )
    publication_state: Mapped[PublicationState] = mapped_column(
        publication_state_enum, default=PublicationState.DRAFT, index=True
    )

    measure: Mapped[Measure] = relationship(back_populates="comparisons")
    affected_fields: Mapped[list["MeasureComparisonField"]] = relationship(
        back_populates="comparison", cascade="all, delete-orphan"
    )


class MeasureComparisonField(Base):
    __tablename__ = "measure_comparison_fields"
    __table_args__ = (UniqueConstraint("comparison_id", "field"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    comparison_id: Mapped[int] = mapped_column(
        ForeignKey("measure_comparisons.id", ondelete="CASCADE")
    )
    field: Mapped[AffectedField] = mapped_column(affected_field_enum)

    comparison: Mapped[MeasureComparison] = relationship(back_populates="affected_fields")
