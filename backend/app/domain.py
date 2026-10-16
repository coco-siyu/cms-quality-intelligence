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
