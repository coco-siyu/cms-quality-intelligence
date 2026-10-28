export type ChangeStatus = "added" | "removed" | "modified" | "unchanged" | "unknown";

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
