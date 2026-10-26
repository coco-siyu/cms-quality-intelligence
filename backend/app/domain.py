from enum import StrEnum


class PublicationState(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    WITHDRAWN = "withdrawn"


class PublicVerificationStatus(StrEnum):
    VERIFIED = "verified"
    PARTIALLY_VERIFIED = "partially_verified"
    SOURCE_UPDATE_DETECTED = "source_update_detected"


class FieldAvailability(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNRESOLVED = "unresolved"


class CollectionType(StrEnum):
    PROGRAM_ROSTER = "program_roster"
    ECQM = "ecqm"
    MIPS_CQM = "mips_cqm"
    MEDICARE_CQM = "medicare_cqm"
    CAHPS_SURVEY = "cahps_survey"
    ADMINISTRATIVE_CLAIMS = "administrative_claims"


class CandidateReviewDecision(StrEnum):
    PENDING = "pending"
    APPROVE = "approve"
    NEEDS_REVISION = "needs_revision"
    NOT_APPLICABLE = "not_applicable"


class FieldPublicationEligibility(StrEnum):
    ELIGIBLE = "eligible"
    PUBLISHED = "published"
    NOT_APPROVED = "not_approved"
    MISSING_SOURCE_EXCERPT = "missing_source_excerpt"
    UNSUPPORTED_FIELD = "unsupported_field"
    STALE_SOURCE = "stale_source"
    UNVERIFIED_SOURCE = "unverified_source"
    UNVERIFIED_MEMBERSHIP = "unverified_membership"
    FIELD_CONFLICT = "field_conflict"


class SourceCheckOutcome(StrEnum):
    NEW_REVISION = "new_revision"
    UNCHANGED = "unchanged"
    REPROCESSED = "reprocessed"
    FAILED = "failed"


class SourceExtractionStatus(StrEnum):
    EXTRACTED = "extracted"
    MANUAL_REVIEW = "manual_review"
    FAILED = "failed"


class ChangeStatus(StrEnum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"
    UNKNOWN = "unknown"


class AffectedField(StrEnum):
    MEASURE_SET = "measure_set"
    DEFINITION = "definition"
    NUMERATOR = "numerator"
    DENOMINATOR = "denominator"
    EXCLUSIONS = "exclusions"
    ELIGIBILITY = "eligibility"
    CALCULATION_LOGIC = "calculation_logic"
