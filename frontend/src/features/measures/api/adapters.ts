import type { DemoFilters, DemoMeasure, DemoReviewStatus } from "../demo/types";
import type {
  AffectedField,
  PublicMeasureSummary,
  VerificationStatus,
} from "./types";

const fieldLabels: Record<AffectedField, string> = {
  measure_set: "Measure set",
  definition: "Definition",
  numerator: "Numerator",
  denominator: "Denominator",
  exclusions: "Exclusions",
  eligibility: "Eligibility",
  calculation_logic: "Calculation logic",
};

const fieldParameters = Object.fromEntries(
  Object.entries(fieldLabels).map(([key, label]) => [label, key]),
) as Record<string, AffectedField>;

const reviewParameters: Record<string, VerificationStatus> = {
  Approved: "verified",
  "In review": "partially_verified",
  "Needs re-verification": "source_update_detected",
};

const reviewLabels: Record<VerificationStatus, DemoReviewStatus> = {
  verified: "Approved",
  partially_verified: "In review",
  source_update_detected: "Needs re-verification",
};

function displayDate(value: string | null): string {
  if (!value) return "Not verified";
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(value));
}

export function filtersToApiFilters(filters: DemoFilters) {
  return {
    q: filters.q || undefined,
    performance_year: filters.year === "all" ? undefined : Number(filters.year),
    from_year: Number(filters.from),
    to_year: Number(filters.to),
    change_status: filters.status === "all" ? undefined : filters.status,
    affected_field: filters.field === "all" ? undefined : fieldParameters[filters.field],
    verification_status: filters.review === "all" ? undefined : reviewParameters[filters.review],
  };
}

export function filtersToApiParameters(filters: DemoFilters) {
  return {
    ...filtersToApiFilters(filters),
    page_size: 100,
  };
}

export function apiSummaryToMeasure(summary: PublicMeasureSummary): DemoMeasure {
  return {
    id: summary.measure_id,
    name: summary.name,
    description: summary.description,
    status: summary.change_status,
    field:
      summary.affected_fields.map((field) => fieldLabels[field]).join(", ") ||
      "No approved change field",
    years: summary.performance_years,
    review: reviewLabels[summary.freshness.verification_status],
    verified: displayDate(summary.freshness.last_verified_at),
    specs: [],
    unavailable: false,
  };
}

export function labelField(field: AffectedField): string {
  return fieldLabels[field];
}

export function formatApiDate(value: string | null): string {
  return displayDate(value);
}
