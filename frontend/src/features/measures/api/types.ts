export type ChangeStatus =
  | "added"
  | "removed"
  | "modified"
  | "wording_only"
  | "unchanged"
  | "unknown";

export type AffectedField =
  | "measure_set"
  | "definition"
  | "numerator"
  | "denominator"
  | "exclusions"
  | "eligibility"
  | "calculation_logic";

export type VerificationStatus =
  | "verified"
  | "partially_verified"
  | "source_update_detected";

export type FieldAvailability = "available" | "unavailable" | "unresolved";

export type EvidenceReference = {
  evidence_id: string;
  source_revision_id: string;
  document_title: string;
  official_url: string;
  publication_date: string | null;
  locator: string | null;
  excerpt: string;
};

export type Freshness = {
  last_verified_at: string | null;
  last_source_check_at: string;
  verification_status: VerificationStatus;
  newer_revision_detected: boolean;
};

export type SpecificationField = {
  field: AffectedField;
  availability: FieldAvailability;
  value: string | null;
  evidence: EvidenceReference[];
};

export type ChangeEvidenceSide = "from_version" | "to_version" | "context";
export type ComparisonEvidenceStatus = "pending" | "verified" | "incomplete";

export type CollectionType =
  | "program_roster"
  | "ecqm"
  | "mips_cqm"
  | "medicare_cqm"
  | "cahps_survey"
  | "administrative_claims";

export type ChangeFieldEvidence = EvidenceReference & {
  side: ChangeEvidenceSide;
};

export type ChangeField = {
  field: AffectedField;
  status: ChangeStatus;
  from_availability: FieldAvailability;
  to_availability: FieldAvailability;
  from_value: string | null;
  to_value: string | null;
  evidence: ChangeFieldEvidence[];
};

export type PublicChangeRecord = {
  measure_id: string;
  measure_name: string;
  program: string;
  collection_type: CollectionType;
  from_year: number;
  to_year: number;
  status: ChangeStatus;
  evidence_status: ComparisonEvidenceStatus;
  approved_at: string;
  published_at: string;
  fields: ChangeField[];
};

export type PublicChangePage = {
  items: PublicChangeRecord[];
  pagination: {
    page: number;
    page_size: number;
    total_items: number;
    total_pages: number;
  };
};

export type MeasureVersion = {
  version_id: string;
  performance_year: number;
  program: string;
  is_program_member: boolean;
  fields: SpecificationField[];
};

export type PublicMeasureSummary = {
  measure_id: string;
  name: string;
  description: string;
  performance_years: number[];
  change_status: ChangeStatus;
  affected_fields: AffectedField[];
  freshness: Freshness;
};

export type PublicMeasureDetail = PublicMeasureSummary & {
  versions: MeasureVersion[];
};

export type PublicMeasurePage = {
  items: PublicMeasureSummary[];
  pagination: {
    page: number;
    page_size: number;
    total_items: number;
    total_pages: number;
  };
};

export type PublicMeasureNavigation = {
  measure_id: string;
  position: number;
  total_items: number;
  previous_measure_id: string | null;
  next_measure_id: string | null;
};

export type PerformanceYearList = {
  years: number[];
  default_from_year: number;
  default_to_year: number;
};

export type ApiErrorPayload = {
  code: string;
  message: string;
  details: Record<string, unknown>[];
};
