import { describe, expect, it } from "vitest";

import type {
  AdminFieldCandidate,
  AdminMeasureDetail,
  AdminMeasureVersion,
} from "../features/admin/api";
import {
  buildCandidateReviewContext,
  candidateTextComparison,
  extractionSignal,
} from "../features/admin/reviewContext";

function candidate(
  reviewItemId: string,
  value: string,
  extractionStatus = "candidate_extracted_needs_sme_review",
): AdminFieldCandidate {
  return {
    review_item_id: reviewItemId,
    field_name: "definition",
    candidate_value: value,
    extraction_status: extractionStatus,
    evidence_locator: "PDF page 4",
    review_decision: "pending",
    reviewed_value: null,
    reviewer_name: null,
    reviewed_at: null,
    reviewer_notes: null,
    source_id: "CMS-SOURCE",
    source_revision_id: `${reviewItemId}-R1`,
    source_title: "Official CMS source",
    official_url: "https://www.cms.gov/example",
    source_content_hash: `${reviewItemId}-hash`,
    review_history: [],
  };
}

function version(
  year: number,
  collectionType: string,
  candidates: AdminFieldCandidate[],
): AdminMeasureVersion {
  return {
    version_id: `CMS-001-PY${year}-${collectionType}`,
    performance_year: year,
    program: "Medicare Shared Savings Program — APP Plus",
    collection_type: collectionType,
    specification_identifier: `CMS001v${year - 2012}`,
    publication_state: "draft",
    verification_status: "partially_verified",
    newer_revision_detected: false,
    last_source_check_at: "2026-10-21T12:00:00Z",
    candidates,
  };
}

function detail(versions: AdminMeasureVersion[]): AdminMeasureDetail {
  return {
    measure_id: "001",
    name: "Source-backed test measure",
    description: "Private review fixture.",
    is_public: false,
    memberships: [],
    versions,
  };
}

describe("admin candidate review context", () => {
  it("pairs the same field and collection type across performance years", () => {
    const prior = candidate("PY2025-ECQM-definition", "Prior wording");
    const current = candidate("PY2026-ECQM-definition", "Current wording");
    const otherCollection = candidate("PY2026-MIPSCQM-definition", "Other collection");

    const context = buildCandidateReviewContext(
      detail([
        version(2025, "ecqm", [prior]),
        version(2026, "ecqm", [current]),
        version(2026, "mips_cqm", [otherCollection]),
      ]),
      prior.review_item_id,
    );

    expect(context?.from?.candidate).toBe(prior);
    expect(context?.to?.candidate).toBe(current);
    expect(context?.comparison.state).toBe("different");
  });

  it("labels whitespace-only differences as matching without making a clinical claim", () => {
    const result = candidateTextComparison(
      candidate("from", "Same   candidate\nvalue"),
      candidate("to", "Same candidate value"),
    );

    expect(result.state).toBe("same");
    expect(result.label).toBe("Extracted wording matches");
  });

  it("does not infer addition or removal when a counterpart is missing", () => {
    const current = candidate("PY2026-ECQM-definition", "Current wording");
    const context = buildCandidateReviewContext(
      detail([version(2026, "ecqm", [current])]),
      current.review_item_id,
    );

    expect(context?.from).toBeUndefined();
    expect(context?.comparison.state).toBe("missing");
    expect(context?.comparison.description).toMatch(/Do not interpret/);
  });

  it("turns extraction codes into explicit reviewer guidance", () => {
    expect(extractionSignal("candidate_extracted_needs_sme_review").label).toBe(
      "SME confirmation needed",
    );
    expect(extractionSignal("manual_extraction_or_policy_review_required").tone).toBe(
      "manual",
    );
    expect(extractionSignal("not_applicable_candidate_needs_sme_confirmation").label).toBe(
      "Applicability confirmation",
    );
  });
});
