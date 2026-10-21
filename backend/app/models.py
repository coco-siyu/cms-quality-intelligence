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
    CollectionType,
    FieldAvailability,
    PublicationState,
    PublicVerificationStatus,
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    revisions: Mapped[list["SourceRevision"]] = relationship(
        back_populates="source_document", cascade="all, delete-orphan"
    )


class SourceRevision(Base):
    __tablename__ = "source_revisions"
    __table_args__ = (
        UniqueConstraint("source_document_id", "revision_number"),
        UniqueConstraint("source_document_id", "content_hash"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    revision_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    source_document_id: Mapped[int] = mapped_column(
        ForeignKey("source_documents.id", ondelete="RESTRICT")
    )
    revision_number: Mapped[int] = mapped_column(Integer)
    content_hash: Mapped[str] = mapped_column(String(128))
    publication_date: Mapped[date | None] = mapped_column(Date)
    effective_date: Mapped[date | None] = mapped_column(Date)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_source_check_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
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


class SpecificationFieldCandidate(Base):
    __tablename__ = "specification_field_candidates"
    __table_args__ = (
        UniqueConstraint("measure_version_id", "field_name"),
        CheckConstraint(
            "(review_decision = 'pending' AND reviewed_at IS NULL) OR "
            "(review_decision != 'pending' AND reviewed_at IS NOT NULL)",
            name="ck_candidate_review_timestamp",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    review_item_id: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    measure_version_id: Mapped[int] = mapped_column(
        ForeignKey("measure_versions.id", ondelete="CASCADE")
    )
    field_name: Mapped[str] = mapped_column(String(80))
    candidate_value: Mapped[str] = mapped_column(Text)
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    measure_version: Mapped[MeasureVersion] = relationship(back_populates="field_candidates")
    source_revision: Mapped[SourceRevision] = relationship(back_populates="field_candidates")
    reviews: Mapped[list["SpecificationFieldCandidateReview"]] = relationship(
        back_populates="field_candidate", cascade="all, delete-orphan"
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
