import type {
  AdminFieldCandidate,
  AdminMeasureDetail,
  AdminMeasureVersion,
} from "./api";

export const ADMIN_FROM_YEAR = 2025;
export const ADMIN_TO_YEAR = 2026;

export type AdminCandidateContext = {
  candidate: AdminFieldCandidate;
  version: AdminMeasureVersion;
};

export type ExtractionSignal = {
  label: string;
  description: string;
  tone: "review" | "manual" | "applicability";
};

export function extractionSignal(status: string): ExtractionSignal {
  switch (status) {
    case "candidate_extracted_needs_sme_review":
      return {
        label: "SME confirmation needed",
        description:
          "A candidate value was extracted, but a subject-matter reviewer has not verified it.",
        tone: "review",
      };
    case "manual_extraction_or_policy_review_required":
      return {
        label: "Manual source review",
        description:
          "No complete normalized value was extracted. Inspect the cited source before deciding.",
        tone: "manual",
      };
    case "not_applicable_candidate_needs_sme_confirmation":
      return {
        label: "Applicability confirmation",
        description:
          "The field may not apply to this variant, but a reviewer must confirm that interpretation.",
        tone: "applicability",
      };
    default:
      return {
        label: "Unclassified review state",
        description:
          "The extraction state is not recognized. Inspect the source and record a cautious decision.",
        tone: "manual",
      };
  }
}

function normalizeCandidateText(value: string) {
  return value.replace(/\s+/g, " ").trim();
}

export function candidateTextComparison(
  fromCandidate?: AdminFieldCandidate,
  toCandidate?: AdminFieldCandidate,
) {
  if (!fromCandidate || !toCandidate) {
    return {
      state: "missing" as const,
      label: "One year has no staged counterpart",
      description:
        "Do not interpret the missing candidate as a verified addition or removal without membership evidence.",
    };
  }
  if (
    normalizeCandidateText(fromCandidate.candidate_value) ===
    normalizeCandidateText(toCandidate.candidate_value)
  ) {
    return {
      state: "same" as const,
      label: "Extracted wording matches",
      description:
        "The candidate text matches after whitespace normalization; each year still requires source review.",
    };
  }
  return {
    state: "different" as const,
    label: "Extracted wording differs",
    description:
      "This is a text comparison only. A reviewer must determine whether the difference is meaningful.",
  };
}

export function buildCandidateReviewContext(
  detail: AdminMeasureDetail,
  reviewItemId: string,
) {
  const contexts = detail.versions.flatMap((version) =>
    version.candidates.map((candidate) => ({ candidate, version })),
  );
  const selected = contexts.find(
    ({ candidate }) => candidate.review_item_id === reviewItemId,
  );
  if (!selected) return undefined;

  const matchingContext = (performanceYear: number) =>
    contexts.find(
      ({ candidate, version }) =>
        version.performance_year === performanceYear &&
        version.collection_type === selected.version.collection_type &&
        candidate.field_name === selected.candidate.field_name,
    );

  const from = matchingContext(ADMIN_FROM_YEAR);
  const to = matchingContext(ADMIN_TO_YEAR);
  return {
    selected,
    from,
    to,
    comparison: candidateTextComparison(from?.candidate, to?.candidate),
  };
}
