import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { createAppRouter } from "../router";
import type { AdminComparison, AdminReviewChecklist } from "../features/admin/api";

function jsonResponse(value: unknown, status = 200) {
  return new Response(JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

async function renderRoute(path: string) {
  const history = createMemoryHistory({ initialEntries: [path] });
  const router = createAppRouter(history);
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  await router.load();
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return router;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("private admin review workspace", () => {
  it("shows exact local setup guidance when authentication is not configured", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse({ configured: false, authenticated: false, username: null }),
      ),
    );

    await renderRoute("/admin");

    expect(
      await screen.findByText("Administrator access is not configured."),
    ).toBeInTheDocument();
    expect(screen.getByText(/generate_admin_credentials/)).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("authenticates and loads only API-backed private review records", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/admin/session") && init?.method === "POST") {
        return Promise.resolve(
          jsonResponse({ configured: true, authenticated: true, username: "reviewer" }),
        );
      }
      if (url.endsWith("/api/admin/session")) {
        return Promise.resolve(
          jsonResponse({ configured: true, authenticated: false, username: null }),
        );
      }
      if (url.endsWith("/api/admin/review-summary")) {
        return Promise.resolve(
          jsonResponse({
            private_measures: 8,
            draft_versions: 46,
            pending_candidates: 352,
            decided_candidates: 0,
            source_revisions: 16,
            newer_revision_flags: 0,
          }),
        );
      }
      if (url.includes("/api/admin/review-dashboard")) {
        return Promise.resolve(
          jsonResponse({
            summary: { total: 0, pending: 0, in_review: 0, completed: 0, needs_re_review: 0 },
            items: [],
          }),
        );
      }
      if (url.includes("/api/admin/measures?")) {
        return Promise.resolve(
          jsonResponse({
            items: [
              {
                measure_id: "001",
                name: "Diabetes: Glycemic Status Assessment Greater Than 9%",
                description: "Source-derived draft record.",
                performance_years: [2025, 2026],
                draft_versions: 8,
                pending_candidates: 88,
                decided_candidates: 0,
                source_documents: 4,
                newer_revision_detected: false,
                last_source_check_at: "2026-10-20T12:00:00Z",
              },
            ],
            pagination: { page: 1, page_size: 100, total_items: 1, total_pages: 1 },
          }),
        );
      }
      if (url.includes("/api/admin/comparisons?")) {
        return Promise.resolve(jsonResponse({ items: [] }));
      }
      return Promise.reject(new Error(`Unexpected request: ${url}`));
    });
    vi.stubGlobal("fetch", fetchMock);

    await renderRoute("/admin");
    fireEvent.change(await screen.findByLabelText("Username"), {
      target: { value: "reviewer" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "not-a-real-password" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Enter review workspace" }));

    expect(
      await screen.findByText("Diabetes: Glycemic Status Assessment Greater Than 9%"),
    ).toBeInTheDocument();
    expect(screen.getByText("352")).toBeInTheDocument();
    expect(screen.getByText("Pending fields")).toBeInTheDocument();
    expect(screen.getByText(/Review decisions stay private/i)).toBeInTheDocument();
    expect(screen.queryByText("DEMO-001")).not.toBeInTheDocument();
    await waitFor(() => {
      expect(fetchMock.mock.calls.every((call) => call[1]?.credentials === "include")).toBe(true);
    });
  });

  it("filters centralized review progress and links to the private measure view", async () => {
    const summary = {
      total: 2,
      pending: 0,
      in_review: 1,
      completed: 0,
      needs_re_review: 1,
    };
    const inReview = {
      comparison_id: 41,
      measure_id: "001",
      measure_name: "Diabetes: Glycemic Status Assessment Greater Than 9%",
      program: "Medicare Shared Savings Program — APP Plus",
      from_year: 2025,
      to_year: 2026,
      dashboard_status: "in_review",
      review_id: "CMS-REVIEW-001",
      review_status: "in_review",
      remaining_tasks: 2,
      progress: { total: 3, open: 2, resolved: 1 },
    };
    const needsReview = {
      ...inReview,
      comparison_id: 42,
      measure_id: "113",
      measure_name: "Colorectal Cancer Screening",
      dashboard_status: "needs_re_review",
      review_id: "CMS-REVIEW-113",
      review_status: "needs_re_review",
      remaining_tasks: 1,
      progress: { total: 2, open: 1, resolved: 1 },
    };
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/admin/session")) {
        return Promise.resolve(
          jsonResponse({ configured: true, authenticated: true, username: "reviewer" }),
        );
      }
      if (url.endsWith("/api/admin/review-summary")) {
        return Promise.resolve(
          jsonResponse({
            private_measures: 2,
            draft_versions: 4,
            pending_candidates: 0,
            decided_candidates: 0,
            source_revisions: 4,
            newer_revision_flags: 1,
          }),
        );
      }
      if (url.includes("/api/admin/review-dashboard?status=needs_re_review")) {
        return Promise.resolve(jsonResponse({ summary, items: [needsReview] }));
      }
      if (url.endsWith("/api/admin/review-dashboard")) {
        return Promise.resolve(jsonResponse({ summary, items: [needsReview, inReview] }));
      }
      if (url.includes("/api/admin/measures?")) {
        return Promise.resolve(
          jsonResponse({
            items: [],
            pagination: { page: 1, page_size: 100, total_items: 0, total_pages: 0 },
          }),
        );
      }
      if (url.includes("/api/admin/comparisons?")) {
        return Promise.resolve(jsonResponse({ items: [] }));
      }
      return Promise.reject(new Error(`Unexpected request: ${url}`));
    });
    vi.stubGlobal("fetch", fetchMock);

    await renderRoute("/admin");

    expect(await screen.findByRole("heading", { name: "Measure review dashboard" }))
      .toBeInTheDocument();
    expect(await screen.findByText("Colorectal Cancer Screening")).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "001 checklist progress" }))
      .toHaveAttribute("aria-valuenow", "1");
    expect(screen.getByRole("progressbar", { name: "001 checklist progress" }))
      .toHaveAttribute("aria-valuemax", "3");
    expect(screen.getByText("2 remaining")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open review for 001" }))
      .toHaveAttribute("href", "/admin/measures/001");

    fireEvent.click(screen.getByRole("button", { name: /Needs re-review/ }));
    await waitFor(() => {
      expect(screen.queryByText(inReview.measure_name)).not.toBeInTheDocument();
    });
    expect(await screen.findByText(needsReview.measure_name)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/admin/review-dashboard?status=needs_re_review"),
      expect.objectContaining({ credentials: "include" }),
    );
  });

  it("prepares, reviews, and publishes an evidence-backed comparison explicitly", async () => {
    const baseComparison: AdminComparison = {
      comparison_id: 41,
      measure_id: "001",
      measure_name: "Diabetes: Glycemic Status Assessment Greater Than 9%",
      program: "Medicare Shared Savings Program — APP Plus",
      collection_type: "program_roster",
      from_year: 2025,
      to_year: 2026,
      status: "modified",
      evidence_status: "verified",
      publication_state: "draft",
      publication_eligibility: "not_approved",
      publication_blocker: "Review and approve this evidence-backed comparison before publication.",
      review_decision: "pending",
      reviewed_at: null,
      reviewer_name: null,
      reviewer_notes: null,
      published_at: null,
      published_by: null,
      created_at: "2026-11-04T12:00:00Z",
      fields: [
        {
          field: "measure_set",
          status: "modified",
          from_availability: "available",
          to_availability: "available",
          from_value: "Member of the PY2025 MSSP APP Plus quality measure set.",
          to_value: "Member of the PY2026 MSSP APP Plus quality measure set.",
          evidence: [
            {
              evidence_id: "CMS-001-2025",
              source_revision_id: "CMS-APP-2025-R1",
              document_title: "PY 2025 APP Quality Requirements",
              official_url: "https://www.cms.gov/example/2025-app",
              publication_date: "2024-11-01",
              effective_date: null,
              locator: "HTML section 'APP Plus Quality Measure Set'; Table 1 rows for 2025",
              excerpt: "Official roster evidence.",
              side: "from_version",
            },
            {
              evidence_id: "CMS-001-2026",
              source_revision_id: "CMS-APP-2026-R1",
              document_title: "PY 2026 APP Quality Requirements",
              official_url: "https://www.cms.gov/example/2026.pdf",
              publication_date: "2025-11-01",
              effective_date: null,
              locator: "PDF pages 3-4; Table 1 'APP Plus Quality Measure Set for PY 2026'",
              excerpt: "Official roster evidence.",
              side: "to_version",
            },
          ],
        },
      ],
      review_history: [],
    };
    const impactOutput = {
      plain_language_summary: {
        statement: "The approved measure-set membership is unchanged across both years.",
        statement_type: "source_fact" as const,
        citations: [{ evidence_id: "CMS-001-2025" }, { evidence_id: "CMS-001-2026" }],
      },
      data_analyst: {
        technical_implications: [
          {
            statement: "Analysts may retain the current year-over-year mapping.",
            statement_type: "possible_impact" as const,
            citations: [{ evidence_id: "CMS-001-2025" }],
          },
        ],
        validation_considerations: [
          {
            statement: "Analysts may rerun the roster validation.",
            statement_type: "possible_impact" as const,
            citations: [{ evidence_id: "CMS-001-2026" }],
          },
        ],
      },
      aco_quality_manager: {
        operational_implications: [
          {
            statement: "Quality teams may keep the current operating plan.",
            statement_type: "possible_impact" as const,
            citations: [{ evidence_id: "CMS-001-2025" }],
          },
        ],
        coordination_considerations: [
          {
            statement: "Quality teams may confirm the roster with reporting partners.",
            statement_type: "possible_impact" as const,
            citations: [{ evidence_id: "CMS-001-2026" }],
          },
        ],
      },
      uncertainty_caveats: [],
    };
    let impactDraft = {
      draft_id: "CMS-IMPACT-001",
      comparison_id: 41,
      provider: "openai",
      model: "test-impact-model",
      prompt_version: "cms-impact-explanation-v1",
      input_digest: "a".repeat(64),
      generation_sequence: 1,
      output: impactOutput,
      review_decision: "pending" as "pending" | "approve" | "reject",
      approved_output: null as typeof impactOutput | null,
      reviewed_at: null as string | null,
      reviewed_by: null as string | null,
      publication_state: "draft" as "draft" | "published" | "withdrawn",
      published_at: null as string | null,
      published_by: null as string | null,
      outdated_at: null,
      cited_evidence_ids: ["CMS-001-2025", "CMS-001-2026"],
      provider_response_id: "response-001",
      created_at: "2026-11-08T12:00:00Z",
      created_by: "reviewer",
    };
    let prepared = false;
    let impactReady = false;
    let comparison: AdminComparison = baseComparison;
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/admin/session")) {
        return Promise.resolve(
          jsonResponse({ configured: true, authenticated: true, username: "reviewer" }),
        );
      }
      if (url.endsWith("/api/admin/review-summary")) {
        return Promise.resolve(
          jsonResponse({
            private_measures: 8,
            draft_versions: 46,
            pending_candidates: 352,
            decided_candidates: 0,
            source_revisions: 16,
            newer_revision_flags: 0,
          }),
        );
      }
      if (url.includes("/api/admin/review-dashboard")) {
        return Promise.resolve(
          jsonResponse({
            summary: { total: 0, pending: 0, in_review: 0, completed: 0, needs_re_review: 0 },
            items: [],
          }),
        );
      }
      if (url.includes("/api/admin/measures?")) {
        return Promise.resolve(
          jsonResponse({
            items: [],
            pagination: { page: 1, page_size: 100, total_items: 0, total_pages: 0 },
          }),
        );
      }
      if (url.includes("/api/admin/comparisons?") && !init?.method) {
        return Promise.resolve(jsonResponse({ items: prepared ? [comparison] : [] }));
      }
      if (url.endsWith("/api/admin/comparisons/generate") && init?.method === "POST") {
        prepared = true;
        return Promise.resolve(
          jsonResponse({ prepared: 1, existing: 0, skipped_measure_ids: ["113", "484"] }),
        );
      }
      if (url.endsWith("/api/admin/comparisons/41") && init?.method === "PATCH") {
        comparison = {
          ...comparison,
          publication_eligibility: "eligible",
          publication_blocker: null,
          review_decision: "approve",
          reviewed_at: "2026-11-04T12:05:00Z",
          reviewer_name: "reviewer",
          reviewer_notes: "Both roster sources support this finding.",
          review_history: [
            {
              decision: "approve",
              reviewer_name: "reviewer",
              reviewed_at: "2026-11-04T12:05:00Z",
              reviewer_notes: "Both roster sources support this finding.",
            },
          ],
        };
        return Promise.resolve(jsonResponse(comparison));
      }
      if (url.endsWith("/api/admin/comparisons/41/publish") && init?.method === "POST") {
        comparison = {
          ...comparison,
          publication_state: "published",
          publication_eligibility: "published",
          published_at: "2026-11-04T12:06:00Z",
          published_by: "reviewer",
        };
        return Promise.resolve(jsonResponse(comparison));
      }
      if (url.endsWith("/api/admin/comparisons/41/impact-explanations") && !init?.method) {
        return Promise.resolve(jsonResponse({ items: impactReady ? [impactDraft] : [] }));
      }
      if (
        url.endsWith("/api/admin/comparisons/41/impact-explanations/generate") &&
        init?.method === "POST"
      ) {
        impactReady = true;
        return Promise.resolve(jsonResponse(impactDraft));
      }
      if (
        url.endsWith("/api/admin/comparisons/41/impact-explanations/regenerate") &&
        init?.method === "POST"
      ) {
        impactDraft = {
          ...impactDraft,
          draft_id: "CMS-IMPACT-002",
          generation_sequence: 2,
          review_decision: "pending",
          approved_output: null,
          reviewed_at: null,
          reviewed_by: null,
          publication_state: "draft",
          published_at: null,
          published_by: null,
          created_at: "2026-11-08T12:10:00Z",
        };
        return Promise.resolve(jsonResponse(impactDraft));
      }
      if (url.endsWith("/api/admin/impact-explanations/CMS-IMPACT-001") && init?.method === "PATCH") {
        const body = JSON.parse(String(init.body)) as {
          decision: "approve" | "reject";
          output: typeof impactOutput | null;
        };
        impactDraft = {
          ...impactDraft,
          review_decision: body.decision,
          approved_output: body.output,
          reviewed_at: "2026-11-08T12:05:00Z",
          reviewed_by: "reviewer",
        };
        return Promise.resolve(jsonResponse(impactDraft));
      }
      if (url.endsWith("/api/admin/impact-explanations/CMS-IMPACT-001/publish") && init?.method === "POST") {
        impactDraft = {
          ...impactDraft,
          publication_state: "published",
          published_at: "2026-11-08T12:06:00Z",
          published_by: "reviewer",
        };
        return Promise.resolve(jsonResponse(impactDraft));
      }
      return Promise.reject(new Error(`Unexpected request: ${url}`));
    });
    vi.stubGlobal("fetch", fetchMock);

    await renderRoute("/admin");
    expect(await screen.findByText("No private comparisons have been prepared for this year pair."))
      .toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Prepare comparisons" }));
    expect(await screen.findByText("1 prepared · 0 already present · 2 one-sided records safely skipped"))
      .toBeInTheDocument();
    expect(await screen.findByText(baseComparison.measure_name)).toBeInTheDocument();
    fireEvent.click(screen.getByText("Inspect values and 2 evidence links"));
    expect(screen.getByRole("link", { name: /PY 2025 APP Quality Requirements/ }))
      .toHaveAttribute("href", "https://www.cms.gov/example/2025-app");
    expect(screen.getByText("PY2025 · 1 official source")).toBeInTheDocument();
    expect(screen.getByText("PY2026 · 1 official source")).toBeInTheDocument();
    expect(screen.getByText("HTML · Table 1")).toBeInTheDocument();
    expect(screen.getByText("PDF · pp. 3–4 · Table 1")).toBeInTheDocument();
    expect(screen.queryByText(/HTML section 'APP Plus/)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Review comparison 001" }));
    fireEvent.change(screen.getByLabelText(/Reviewer notes/), {
      target: { value: "Both roster sources support this finding." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save comparison review" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());

    const reviewCall = fetchMock.mock.calls.find(
      ([input, init]) => String(input).endsWith("/api/admin/comparisons/41") && init?.method === "PATCH",
    );
    expect(reviewCall?.[1]?.headers).toMatchObject({
      "X-CMSQI-Admin-Action": "review-comparison",
    });
    expect(screen.getByRole("button", { name: "Publish comparison 001" })).toBeEnabled();

    fireEvent.click(screen.getByRole("button", { name: "Publish comparison 001" }));
    expect(await screen.findByText("Published", { selector: "button" })).toBeDisabled();
    const publishCall = fetchMock.mock.calls.find(
      ([input]) => String(input).endsWith("/api/admin/comparisons/41/publish"),
    );
    expect(publishCall?.[1]?.headers).toMatchObject({
      "X-CMSQI-Admin-Action": "publish-comparison",
    });

    fireEvent.click(screen.getByRole("button", { name: "Review AI impact 001" }));
    expect(await screen.findByRole("heading", { name: "001 · Potential impact" }))
      .toBeInTheDocument();
    expect(await screen.findByText("No generated explanation is ready."))
      .toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Generate explanation" }));
    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(([input]) =>
          String(input).endsWith(
            "/api/admin/comparisons/41/impact-explanations/generate",
          ),
        ),
      ).toBe(true);
    });
    const generationCall = fetchMock.mock.calls.find(([input]) =>
      String(input).endsWith("/api/admin/comparisons/41/impact-explanations/generate"),
    );
    expect(generationCall?.[1]?.headers).toMatchObject({
      "X-CMSQI-Admin-Action": "generate-impact-explanation",
    });
    fireEvent.change(await screen.findByLabelText("Technical implications 1"), {
      target: { value: "Analysts may retain the reviewed year-over-year mapping." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Approve pair" }));
    expect(await screen.findByRole("button", { name: "Publish explanation" })).toBeEnabled();

    const impactReviewCall = fetchMock.mock.calls.find(
      ([input, init]) =>
        String(input).endsWith("/api/admin/impact-explanations/CMS-IMPACT-001") &&
        init?.method === "PATCH",
    );
    expect(impactReviewCall?.[1]?.headers).toMatchObject({
      "X-CMSQI-Admin-Action": "review-impact-explanation",
    });
    expect(JSON.parse(String(impactReviewCall?.[1]?.body)).output.data_analyst
      .technical_implications[0].statement)
      .toBe("Analysts may retain the reviewed year-over-year mapping.");

    fireEvent.click(screen.getByRole("button", { name: "Publish explanation" }));
    expect(await within(screen.getByRole("dialog")).findByText("Published"))
      .toBeInTheDocument();
    const impactPublishCall = fetchMock.mock.calls.find(
      ([input]) =>
        String(input).endsWith("/api/admin/impact-explanations/CMS-IMPACT-001/publish"),
    );
    expect(impactPublishCall?.[1]?.headers).toMatchObject({
      "X-CMSQI-Admin-Action": "publish-impact-explanation",
    });

    fireEvent.click(screen.getByRole("button", { name: "Regenerate" }));
    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(([input]) =>
          String(input).endsWith(
            "/api/admin/comparisons/41/impact-explanations/regenerate",
          ),
        ),
      ).toBe(true);
    });
    const regenerationCall = fetchMock.mock.calls.find(([input]) =>
      String(input).endsWith(
        "/api/admin/comparisons/41/impact-explanations/regenerate",
      ),
    );
    expect(regenerationCall?.[1]?.headers).toMatchObject({
      "X-CMSQI-Admin-Action": "regenerate-impact-explanation",
    });
    expect(await screen.findByRole("button", { name: "Approve pair" })).toBeEnabled();
  });

  it("manages generated and manual impact tasks in one role-filtered checklist", async () => {
    const comparison: AdminComparison = {
      comparison_id: 41,
      measure_id: "001",
      measure_name: "Diabetes: Glycemic Status Assessment Greater Than 9%",
      program: "Medicare Shared Savings Program — APP Plus",
      collection_type: "program_roster",
      from_year: 2025,
      to_year: 2026,
      status: "unchanged",
      evidence_status: "verified",
      publication_state: "published",
      publication_eligibility: "published",
      publication_blocker: null,
      review_decision: "approve",
      reviewed_at: "2026-11-04T12:05:00Z",
      reviewer_name: "reviewer",
      reviewer_notes: null,
      published_at: "2026-11-04T12:06:00Z",
      published_by: "reviewer",
      created_at: "2026-11-04T12:00:00Z",
      fields: [],
      review_history: [],
    };
    const evidence = {
      evidence_id: "CMS-001-2026",
      source_revision_id: "CMS-APP-2026-R1",
      document_title: "PY 2026 APP Quality Requirements",
      official_url: "https://www.cms.gov/example/2026.pdf",
      publication_date: "2025-11-01",
      effective_date: null,
      locator: "PDF pages 3-4",
      excerpt: "Official roster evidence.",
      side: "to_version" as const,
    };
    let checklist: AdminReviewChecklist = {
      comparison_id: 41,
      review_id: null as string | null,
      review_status: null,
      eligible_impact_explanation_draft_id: "CMS-IMPACT-001",
      proposals: [],
      items: [],
      progress: { total: 0, open: 0, resolved: 0 },
      signoffs: [],
      can_sign_off: false,
      signoff_blocker: "Start the review before signing off.",
    };
    const refreshProgress = () => {
      const open = checklist.items.filter((item) => item.status === "open").length;
      checklist.progress = {
        total: checklist.items.length,
        open,
        resolved: checklist.items.length - open,
      };
      checklist.can_sign_off = Boolean(checklist.review_id) && open === 0 && checklist.review_status !== "completed";
      checklist.signoff_blocker = checklist.can_sign_off
        ? null
        : checklist.review_status === "completed"
          ? "This review is already signed off. Reopen it before signing off again."
          : open > 0
            ? `${open} accepted task${open === 1 ? " remains" : "s remain"} unresolved.`
            : "Start the review before signing off.";
    };
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/admin/session")) {
        return Promise.resolve(
          jsonResponse({ configured: true, authenticated: true, username: "reviewer" }),
        );
      }
      if (url.endsWith("/api/admin/review-summary")) {
        return Promise.resolve(
          jsonResponse({
            private_measures: 1,
            draft_versions: 2,
            pending_candidates: 0,
            decided_candidates: 0,
            source_revisions: 2,
            newer_revision_flags: 0,
          }),
        );
      }
      if (url.includes("/api/admin/review-dashboard")) {
        return Promise.resolve(
          jsonResponse({
            summary: { total: 1, pending: 0, in_review: 1, completed: 0, needs_re_review: 0 },
            items: [],
          }),
        );
      }
      if (url.includes("/api/admin/measures?")) {
        return Promise.resolve(
          jsonResponse({
            items: [],
            pagination: { page: 1, page_size: 100, total_items: 0, total_pages: 0 },
          }),
        );
      }
      if (url.includes("/api/admin/comparisons?") && !init?.method) {
        return Promise.resolve(jsonResponse({ items: [comparison] }));
      }
      if (url.endsWith("/api/admin/comparisons/41/review-checklist") && !init?.method) {
        return Promise.resolve(jsonResponse(checklist));
      }
      if (
        url.endsWith("/api/admin/impact-explanations/CMS-IMPACT-001/task-proposals/generate") &&
        init?.method === "POST"
      ) {
        checklist = {
          ...checklist,
          review_id: "CMS-REVIEW-001",
          review_status: "pending",
          proposals: [
            {
              proposal_id: "PROPOSAL-ANALYST",
              review_id: "CMS-REVIEW-001",
              impact_explanation_draft_id: "CMS-IMPACT-001",
              sequence: 1,
              role: "data_analyst",
              title: "Validate the year-specific mapping",
              description: "Compare the reviewed mapping with the official evidence.",
              status: "pending",
              evidence: [evidence],
              provider: "openai",
              model: "test-model",
              prompt_version: "v1",
              input_digest: "a".repeat(64),
              provider_response_id: "response-1",
              decided_at: null,
              decided_by: null,
              created_at: "2026-11-10T12:00:00Z",
              created_by: "reviewer",
            },
            {
              proposal_id: "PROPOSAL-MANAGER",
              review_id: "CMS-REVIEW-001",
              impact_explanation_draft_id: "CMS-IMPACT-001",
              sequence: 2,
              role: "aco_quality_manager",
              title: "Confirm the reporting handoff",
              description: "Review the operational handoff with the quality team.",
              status: "pending",
              evidence: [evidence],
              provider: "openai",
              model: "test-model",
              prompt_version: "v1",
              input_digest: "b".repeat(64),
              provider_response_id: "response-1",
              decided_at: null,
              decided_by: null,
              created_at: "2026-11-10T12:00:00Z",
              created_by: "reviewer",
            },
          ],
        };
        return Promise.resolve(jsonResponse({ items: checklist.proposals }));
      }
      if (url.endsWith("/api/admin/task-proposals/PROPOSAL-ANALYST/accept")) {
        checklist.proposals[0] = { ...checklist.proposals[0], status: "accepted" };
        checklist.items.push({
          checklist_item_id: "CHECKLIST-1",
          review_id: "CMS-REVIEW-001",
          accepted_from_proposal_id: "PROPOSAL-ANALYST",
          role: "data_analyst",
          title: "Validate the year-specific mapping",
          description: "Compare the reviewed mapping with the official evidence.",
          status: "open",
          notes: null,
          resolved_at: null,
          resolved_by: null,
          created_at: "2026-11-10T12:05:00Z",
          created_by: "reviewer",
          updated_at: "2026-11-10T12:05:00Z",
        });
        checklist.review_status = "in_review";
        refreshProgress();
        return Promise.resolve(jsonResponse(checklist));
      }
      if (url.endsWith("/api/admin/comparisons/41/review-checklist/items")) {
        const body = JSON.parse(String(init?.body));
        checklist.items.push({
          checklist_item_id: "CHECKLIST-2",
          review_id: "CMS-REVIEW-001",
          accepted_from_proposal_id: null,
          ...body,
          status: "open",
          resolved_at: null,
          resolved_by: null,
          created_at: "2026-11-10T12:06:00Z",
          created_by: "reviewer",
          updated_at: "2026-11-10T12:06:00Z",
        });
        refreshProgress();
        return Promise.resolve(jsonResponse(checklist));
      }
      if (url.endsWith("/api/admin/review-checklist/items/CHECKLIST-1")) {
        const body = JSON.parse(String(init?.body));
        checklist.items[0] = {
          ...checklist.items[0],
          ...body,
          resolved_at: body.status === "open" ? null : "2026-11-10T12:07:00Z",
          resolved_by: body.status === "open" ? null : "reviewer",
        };
        refreshProgress();
        return Promise.resolve(jsonResponse(checklist));
      }
      if (url.endsWith("/api/admin/review-checklist/items/CHECKLIST-2")) {
        const body = JSON.parse(String(init?.body));
        checklist.items[1] = {
          ...checklist.items[1],
          ...body,
          resolved_at: body.status === "open" ? null : "2026-11-10T12:08:00Z",
          resolved_by: body.status === "open" ? null : "reviewer",
        };
        refreshProgress();
        return Promise.resolve(jsonResponse(checklist));
      }
      if (url.endsWith("/api/admin/reviews/CMS-REVIEW-001/sign-off")) {
        const body = JSON.parse(String(init?.body)) as { note: string | null };
        checklist = {
          ...checklist,
          review_status: "completed",
          signoffs: [
            ...checklist.signoffs,
            {
              signoff_id: "SIGNOFF-1",
              sequence: 1,
              accepted_task_count: 2,
              resolved_task_count: 2,
              note: body.note,
              signed_at: "2026-11-10T12:09:00Z",
              signed_by: "reviewer",
            },
          ],
          can_sign_off: false,
          signoff_blocker: "This review is already signed off. Reopen it before signing off again.",
        };
        return Promise.resolve(jsonResponse(checklist));
      }
      if (url.endsWith("/api/admin/reviews/CMS-REVIEW-001/reopen")) {
        checklist = {
          ...checklist,
          review_status: "reopened",
          can_sign_off: true,
          signoff_blocker: null,
        };
        return Promise.resolve(jsonResponse(checklist));
      }
      return Promise.reject(new Error(`Unexpected request: ${url}`));
    });
    vi.stubGlobal("fetch", fetchMock);

    await renderRoute("/admin");
    fireEvent.click(await screen.findByRole("button", { name: "Open checklist 001" }));
    expect(await screen.findByRole("heading", { name: "001 · Impact checklist" }))
      .toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: "Generate" }));
    expect(await screen.findByText("Validate the year-specific mapping"))
      .toBeInTheDocument();
    expect(screen.getByText("Confirm the reporting handoff")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Data Analyst" }));
    expect(screen.queryByText("Confirm the reporting handoff")).not.toBeInTheDocument();
    const suggestion = screen.getByText("Validate the year-specific mapping").closest("article");
    fireEvent.click(within(suggestion!).getByRole("button", { name: "Accept" }));
    await waitFor(() => expect(screen.getByText("0/1")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: "Add task" }));
    fireEvent.change(screen.getByLabelText("New task title"), {
      target: { value: "Document the validation result" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add to checklist" }));
    expect(await screen.findByText("Document the validation result")).toBeInTheDocument();

    const acceptedTask = screen.getByText("Validate the year-specific mapping").closest("article");
    fireEvent.click(within(acceptedTask!).getByRole("button", { name: "Complete" }));
    await waitFor(() => expect(within(acceptedTask!).getByText("Completed")).toBeInTheDocument());
    expect(screen.getByText("1/2")).toBeInTheDocument();

    const manualTask = screen.getByText("Document the validation result").closest("article");
    fireEvent.click(within(manualTask!).getByRole("button", { name: "Complete" }));
    await waitFor(() => expect(screen.getByText("2/2")).toBeInTheDocument());

    fireEvent.change(screen.getByLabelText("Sign-off note (optional)"), {
      target: { value: "All accepted follow-up work is resolved." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Confirm sign-off" }));
    expect(await screen.findByRole("heading", { name: "Signed off" })).toBeInTheDocument();
    expect(screen.getByText(/Sign-off 1 · reviewer/)).toBeInTheDocument();
    expect(within(acceptedTask!).getByRole("button", { name: "Edit" })).toBeDisabled();

    const signoffCall = fetchMock.mock.calls.find(([input]) =>
      String(input).endsWith("/api/admin/reviews/CMS-REVIEW-001/sign-off"),
    );
    expect(signoffCall?.[1]?.headers).toMatchObject({
      "X-CMSQI-Admin-Action": "manage-review-lifecycle",
    });
    expect(JSON.parse(String(signoffCall?.[1]?.body))).toEqual({
      note: "All accepted follow-up work is resolved.",
    });

    fireEvent.click(screen.getByRole("button", { name: "Reopen review" }));
    expect(await screen.findByRole("heading", { name: "Ready for sign-off?" }))
      .toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirm sign-off" })).toBeEnabled();
    expect(within(acceptedTask!).getByRole("button", { name: "Edit" })).toBeEnabled();

    const acceptCall = fetchMock.mock.calls.find(([input]) =>
      String(input).endsWith("/api/admin/task-proposals/PROPOSAL-ANALYST/accept"),
    );
    expect(acceptCall?.[1]?.headers).toMatchObject({
      "X-CMSQI-Admin-Action": "manage-review-checklist",
    });
  });

  it("loads a private measure directly with source provenance", async () => {
    const candidate = {
      review_item_id: "CMS-001-PY2025-ECQM-definition",
      field_name: "definition",
      candidate_value: "Candidate definition requiring human review.",
      source_excerpt: "Verbatim official wording for the 2025 candidate.",
      extraction_status: "candidate_extracted_needs_sme_review",
      evidence_locator: "Page 4",
      review_decision: "pending",
      reviewed_value: null,
      reviewer_name: null,
      reviewed_at: null,
      reviewer_notes: null,
      publication_state: "draft",
      publication_eligibility: "not_approved",
      publication_blocker: "A qualified reviewer must approve this candidate before publication.",
      published_field: null,
      published_at: null,
      published_by: null,
      source_id: "CMS-SOURCE-001",
      source_revision_id: "CMS-SOURCE-001-R1",
      source_title: "Official CMS specification",
      official_url: "https://www.cms.gov/example",
      source_content_hash: "hash",
      review_history: [],
    };
    const nextYearCandidate = {
      ...candidate,
      review_item_id: "CMS-001-PY2026-ECQM-definition",
      candidate_value: "Updated candidate definition requiring human review.",
      source_excerpt: null,
      extraction_status: "manual_extraction_or_policy_review_required",
      evidence_locator: "Page 5",
      source_revision_id: "CMS-SOURCE-001-R2",
    };
    const detail = {
      measure_id: "001",
      name: "Diabetes: Glycemic Status Assessment Greater Than 9%",
      description: "Source-derived draft record.",
      is_public: false,
      memberships: [
        {
          performance_year: 2025,
          program: "Medicare Shared Savings Program — APP Plus",
          is_program_member: true,
          publication_state: "draft",
          verified_at: "2026-10-20T12:00:00Z",
        },
      ],
      versions: [
        {
          version_id: "CMS-001-PY2025-ECQM",
          performance_year: 2025,
          program: "Medicare Shared Savings Program — APP Plus",
          collection_type: "ecqm",
          specification_identifier: "CMS122v13",
          publication_state: "draft",
          verification_status: "partially_verified",
          newer_revision_detected: false,
          last_source_check_at: "2026-10-20T12:00:00Z",
          candidates: [candidate],
        },
        {
          version_id: "CMS-001-PY2026-ECQM",
          performance_year: 2026,
          program: "Medicare Shared Savings Program — APP Plus",
          collection_type: "ecqm",
          specification_identifier: "CMS122v14",
          publication_state: "draft",
          verification_status: "partially_verified",
          newer_revision_detected: false,
          last_source_check_at: "2026-10-20T12:00:00Z",
          candidates: [nextYearCandidate],
        },
      ],
    };
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.includes("/api/admin/review-items/") && init?.method === "PATCH") {
          const request = JSON.parse(String(init.body));
          return Promise.resolve(
            jsonResponse({
              ...candidate,
              review_decision: request.decision,
              reviewed_value: request.reviewed_value,
              reviewer_name: "reviewer",
              reviewed_at: "2026-10-21T18:00:00Z",
              reviewer_notes: request.reviewer_notes,
              publication_eligibility: "eligible",
              publication_blocker: null,
              review_history: [
                {
                  decision: request.decision,
                  reviewed_value: request.reviewed_value,
                  reviewer_name: "reviewer",
                  reviewed_at: "2026-10-21T18:00:00Z",
                  reviewer_notes: request.reviewer_notes,
                },
              ],
            }),
          );
        }
        if (url.endsWith("/publish") && init?.method === "POST") {
          return Promise.resolve(
            jsonResponse({
              ...candidate,
              review_decision: "approve",
              reviewed_value: "Reviewed definition supported by the official source.",
              reviewer_name: "reviewer",
              reviewed_at: "2026-10-21T18:00:00Z",
              publication_state: "published",
              publication_eligibility: "published",
              publication_blocker: null,
              published_field: "definition",
              published_at: "2026-10-22T14:00:00Z",
              published_by: "reviewer",
              review_history: [
                {
                  decision: "approve",
                  reviewed_value: "Reviewed definition supported by the official source.",
                  reviewer_name: "reviewer",
                  reviewed_at: "2026-10-21T18:00:00Z",
                  reviewer_notes: "Confirmed against page 4.",
                },
              ],
            }),
          );
        }
        if (url.endsWith("/api/admin/session")) {
          return Promise.resolve(
            jsonResponse({ configured: true, authenticated: true, username: "reviewer" }),
          );
        }
        if (url.endsWith("/api/admin/measures/001/review-activity")) {
          return Promise.resolve(
            jsonResponse({
              measure_id: "001",
              reviews: [
                {
                  review_id: "CMS-REVIEW-001",
                  comparison_id: 41,
                  review_status: "reopened",
                  program: "Medicare Shared Savings Program — APP Plus",
                  collection_type: "program_roster",
                  from_year: 2025,
                  to_year: 2026,
                  events: [
                    {
                      event_id: "EVENT-2",
                      sequence: 2,
                      event_type: "reopened",
                      title: "Review reopened",
                      detail: "A completed review was reopened for another review pass.",
                      actor: "reviewer",
                      occurred_at: "2026-11-11T14:00:00Z",
                      note: "Confirm the latest official revision.",
                    },
                    {
                      event_id: "EVENT-1",
                      sequence: 1,
                      event_type: "signed_off",
                      title: "Review signed off",
                      detail: "2 of 2 accepted tasks were resolved at sign-off.",
                      actor: "reviewer",
                      occurred_at: "2026-11-10T14:00:00Z",
                      note: "Initial review complete.",
                    },
                  ],
                },
              ],
            }),
          );
        }
        if (url.endsWith("/api/admin/measures/001")) return Promise.resolve(jsonResponse(detail));
        return Promise.reject(new Error(`Unexpected request: ${url}`));
      });
    vi.stubGlobal("fetch", fetchMock);

    await renderRoute("/admin/measures/001");

    expect(
      await screen.findByRole("heading", {
        name: "Diabetes: Glycemic Status Assessment Greater Than 9%",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("Private draft")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Review activity" }))
      .toBeInTheDocument();
    expect(screen.getByText("2 recorded events")).toBeInTheDocument();
    expect(screen.getByText("Review reopened")).toBeInTheDocument();
    expect(screen.getByText("Review signed off")).toBeInTheDocument();
    expect(screen.getByText("Confirm the latest official revision.")).toBeInTheDocument();
    expect(screen.getByText("reviewer · Event 2")).toBeInTheDocument();
    fireEvent.click(screen.getAllByText("definition")[0]);
    expect(screen.getByText("Candidate definition requiring human review.")).toBeVisible();
    expect(screen.getAllByRole("link", { name: /Official CMS specification/ })[0]).toHaveAttribute(
      "href",
      "https://www.cms.gov/example",
    );
    fireEvent.click(screen.getAllByRole("button", { name: "Review candidate" })[0]);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Extracted wording differs")).toBeInTheDocument();
    const priorYear = screen.getByLabelText("PY2025 candidate, active review item");
    const nextYear = screen.getByLabelText("PY2026 candidate");
    expect(within(priorYear).getByText("CMS122v13")).toBeInTheDocument();
    expect(
      within(priorYear).getByText("Verbatim official wording for the 2025 candidate."),
    ).toBeInTheDocument();
    expect(within(priorYear).getByText("SME confirmation needed")).toBeInTheDocument();
    expect(within(nextYear).getByText("CMS122v14")).toBeInTheDocument();
    expect(
      within(nextYear).getByText(/No separate excerpt was captured/),
    ).toBeInTheDocument();
    expect(within(nextYear).getByText("Manual source review")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/Reviewed value/), {
      target: { value: "Reviewed definition supported by the official source." },
    });
    fireEvent.change(screen.getByLabelText(/Reviewer notes \(optional\)/), {
      target: { value: "Confirmed against page 4." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save private review" }));

    expect(await screen.findByText("Approved")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    const mutationCall = fetchMock.mock.calls.find(([input]) =>
      String(input).includes("/api/admin/review-items/"),
    );
    expect(mutationCall?.[1]?.headers).toMatchObject({
      "X-CMSQI-Admin-Action": "review-decision",
    });
    expect(JSON.parse(String(mutationCall?.[1]?.body))).toEqual({
      decision: "approve",
      reviewed_value: "Reviewed definition supported by the official source.",
      reviewer_notes: "Confirmed against page 4.",
    });

    const publishButton = screen
      .getAllByRole("button", { name: "Publish verified field" })
      .find((button) => !(button as HTMLButtonElement).disabled);
    expect(publishButton).toBeDefined();
    fireEvent.click(publishButton!);
    expect(await screen.findByText(/Published as definition/)).toBeInTheDocument();
    const publicationCall = fetchMock.mock.calls.find(([input]) =>
      String(input).endsWith("/publish"),
    );
    expect(publicationCall?.[1]?.method).toBe("POST");
    expect(publicationCall?.[1]?.headers).toMatchObject({
      "X-CMSQI-Admin-Action": "publish-field",
    });

    fireEvent.click(screen.getAllByRole("button", { name: "Review candidate" })[0]);
    expect(screen.getByRole("heading", { name: "Review history" })).toBeInTheDocument();
    expect(screen.getByText(/reviewer · Oct 21, 2026/)).toBeInTheDocument();
  });

  it("loads the private source registry and sends explicitly authorized checks", async () => {
    const source = {
      source_id: "CMS-PY2026-APP-REQ",
      title: "PY 2026 APP Quality Requirements",
      official_url: "https://www.cms.gov/example/py2026-app.pdf",
      source_format: "pdf",
      is_active: true,
      notes: "Official CMS source under review.",
      created_by: "reviewer",
      created_at: "2026-10-26T12:00:00Z",
      updated_at: "2026-10-26T12:00:00Z",
      deactivated_at: null,
      revision_count: 1,
      latest_revision: {
        revision_id: "CMS-PY2026-APP-REQ-R1-abcdef123456",
        revision_number: 1,
        content_hash: "abcdef1234567890",
        source_url: "https://www.cms.gov/example/py2026-app.pdf",
        final_url: "https://www.cms.gov/example/py2026-app.pdf",
        http_status: 200,
        mime_type: "application/pdf",
        byte_length: 2048,
        publication_date: null,
        retrieved_at: "2026-10-26T12:00:00Z",
        last_source_check_at: "2026-10-26T12:00:00Z",
        extraction: {
          extraction_id: "CMS-PY2026-APP-REQ-R1-abcdef123456-X1",
          sequence: 1,
          status: "extracted",
          page_count: 4,
          segment_count: 12,
          error: null,
          extractor_version: "pypdf-v1",
          forced: false,
          extracted_at: "2026-10-26T12:00:00Z",
          created_by: "reviewer",
          normalization: null,
        },
      },
      latest_check: {
        check_id: "CMS-CHECK-1",
        outcome: "new_revision",
        checked_at: "2026-10-26T12:00:00Z",
        requested_url: "https://www.cms.gov/example/py2026-app.pdf",
        final_url: "https://www.cms.gov/example/py2026-app.pdf",
        http_status: 200,
        mime_type: "application/pdf",
        byte_length: 2048,
        content_hash: "abcdef1234567890",
        error: null,
        forced: false,
        checked_by: "reviewer",
        revision_id: "CMS-PY2026-APP-REQ-R1-abcdef123456",
        extraction_id: "CMS-PY2026-APP-REQ-R1-abcdef123456-X1",
      },
    };
    const ingestionRun = {
      run_id: "CMS-INGEST-1",
      status: "running",
      source_count: 1,
      completed_count: 0,
      failed_count: 0,
      started_at: "2026-10-26T12:10:00Z",
      completed_at: null,
      created_by: "reviewer",
      items: [
        {
          item_id: "CMS-INGEST-ITEM-1",
          sequence: 1,
          source_id: source.source_id,
          source_title: source.title,
          stage: "downloading",
          source_check_id: null,
          source_check_outcome: null,
          started_at: "2026-10-26T12:10:00Z",
          completed_at: null,
          error: null,
          events: [
            {
              event_id: "CMS-EVENT-0",
              stage: "pending",
              occurred_at: "2026-10-26T12:09:59Z",
              detail: "Queued for source retrieval.",
            },
            {
              event_id: "CMS-EVENT-1",
              stage: "downloading",
              occurred_at: "2026-10-26T12:10:00Z",
              detail: "Retrieving official CMS source.",
            },
          ],
        },
      ],
    };
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/admin/session")) {
        return Promise.resolve(
          jsonResponse({ configured: true, authenticated: true, username: "reviewer" }),
        );
      }
      if (url.endsWith("/api/admin/sources") && !init?.method) {
        return Promise.resolve(jsonResponse({ items: [source] }));
      }
      if (url.endsWith("/api/admin/ingestion-runs") && init?.method === "POST") {
        return Promise.resolve(jsonResponse(ingestionRun, 202));
      }
      if (url.endsWith("/api/admin/ingestion-runs")) {
        return Promise.resolve(jsonResponse({ items: [] }));
      }
      if (url.endsWith("/api/admin/sources/CMS-PY2026-APP-REQ/check")) {
        return Promise.resolve(jsonResponse({ ...source, revisions: [], checks: [] }));
      }
      if (url.endsWith("/CMS-PY2026-APP-REQ-R1-abcdef123456-X1/normalize")) {
        return Promise.resolve(
          jsonResponse({
            normalization_id: "CMS-NORM-1",
            status: "normalized",
            parser_version: "cms-labeled-fields-v1",
            measure_candidate_count: 1,
            staged_field_count: 2,
            created_at: "2026-10-26T12:01:00Z",
            created_by: "reviewer",
            extraction_id: "CMS-PY2026-APP-REQ-R1-abcdef123456-X1",
            source_id: "CMS-PY2026-APP-REQ",
            revision_id: "CMS-PY2026-APP-REQ-R1-abcdef123456",
            candidates: [],
          }),
        );
      }
      return Promise.reject(new Error(`Unexpected request: ${url}`));
    });
    vi.stubGlobal("fetch", fetchMock);

    await renderRoute("/admin/sources");

    expect(await screen.findByText("PY 2026 APP Quality Requirements")).toBeInTheDocument();
    expect(screen.getByText(/12 text segments/)).toBeInTheDocument();
    expect(screen.queryByText("Loading candidates…")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Check for updates" }));
    expect(
      await screen.findByRole("heading", { name: "Checking official sources" }),
    ).toBeInTheDocument();
    expect(screen.getByText("0 of 1 sources")).toBeInTheDocument();
    expect(screen.getByText("Downloading", { selector: ".ingestion-stage-badge" })).toBeInTheDocument();
    expect(screen.getByText("Processing now")).toBeInTheDocument();
    const runCall = fetchMock.mock.calls.find(
      ([input, init]) =>
        String(input).endsWith("/api/admin/ingestion-runs") && init?.method === "POST",
    );
    expect(runCall?.[1]?.headers).toMatchObject({
      "X-CMSQI-Admin-Action": "check-for-updates",
    });
    fireEvent.click(screen.getByRole("button", { name: "Check source" }));
    await waitFor(() => {
      const checkCall = fetchMock.mock.calls.find(([input]) =>
        String(input).endsWith("/CMS-PY2026-APP-REQ/check"),
      );
      expect(checkCall?.[1]?.headers).toMatchObject({
        "X-CMSQI-Admin-Action": "source-check",
      });
      expect(JSON.parse(String(checkCall?.[1]?.body))).toEqual({ force: false });
    });

    fireEvent.click(screen.getByRole("button", { name: "Normalize candidates" }));
    await waitFor(() => {
      const normalizationCall = fetchMock.mock.calls.find(([input]) =>
        String(input).endsWith("/CMS-PY2026-APP-REQ-R1-abcdef123456-X1/normalize"),
      );
      expect(normalizationCall?.[1]?.headers).toMatchObject({
        "X-CMSQI-Admin-Action": "normalize-source",
      });
    });
  });

  it("distinguishes running, failed, and completed ingestion history", async () => {
    const source = {
      source_id: "CMS-SOURCE-1",
      title: "Official CMS source",
      official_url: "https://www.cms.gov/example/source.html",
      source_format: "html",
      is_active: true,
      notes: null,
      created_by: "reviewer",
      created_at: "2026-10-26T12:00:00Z",
      updated_at: "2026-10-26T12:00:00Z",
      deactivated_at: null,
      revision_count: 0,
      latest_revision: null,
      latest_check: null,
    };
    const item = {
      item_id: "CMS-ITEM-COMPLETE",
      sequence: 1,
      source_id: source.source_id,
      source_title: source.title,
      stage: "unchanged",
      source_check_id: "CMS-CHECK-COMPLETE",
      source_check_outcome: "unchanged",
      started_at: "2026-10-26T12:00:00Z",
      completed_at: "2026-10-26T12:00:02Z",
      error: null,
      events: [
        {
          event_id: "CMS-EVENT-COMPLETE",
          stage: "unchanged",
          occurred_at: "2026-10-26T12:00:02Z",
          detail: "The retrieved content matches an existing immutable revision.",
        },
      ],
    };
    const runs = [
      {
        run_id: "CMS-RUN-COMPLETE",
        status: "completed",
        source_count: 1,
        completed_count: 1,
        failed_count: 0,
        started_at: "2026-10-26T12:00:00Z",
        completed_at: "2026-10-26T12:00:02Z",
        created_by: "reviewer",
        items: [item],
      },
      {
        run_id: "CMS-RUN-FAILED",
        status: "completed_with_errors",
        source_count: 1,
        completed_count: 1,
        failed_count: 1,
        started_at: "2026-10-26T11:00:00Z",
        completed_at: "2026-10-26T11:00:03Z",
        created_by: "reviewer",
        items: [
          {
            ...item,
            item_id: "CMS-ITEM-FAILED",
            stage: "failed",
            source_check_id: "CMS-CHECK-FAILED",
            source_check_outcome: "failed",
            error: "CMS returned HTTP 503 while retrieving the document.",
            events: [
              {
                event_id: "CMS-EVENT-FAILED",
                stage: "failed",
                occurred_at: "2026-10-26T11:00:03Z",
                detail: "CMS returned HTTP 503 while retrieving the document.",
              },
            ],
          },
        ],
      },
      {
        run_id: "CMS-RUN-RUNNING",
        status: "running",
        source_count: 1,
        completed_count: 0,
        failed_count: 0,
        started_at: "2026-10-26T10:00:00Z",
        completed_at: null,
        created_by: "reviewer",
        items: [
          {
            ...item,
            item_id: "CMS-ITEM-RUNNING",
            stage: "extracting",
            source_check_id: null,
            source_check_outcome: null,
            completed_at: null,
            events: [
              {
                event_id: "CMS-EVENT-RUNNING",
                stage: "extracting",
                occurred_at: "2026-10-26T10:00:01Z",
                detail: "Extracting traceable text from the changed source revision.",
              },
            ],
          },
        ],
      },
    ];
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/api/admin/session")) {
          return Promise.resolve(
            jsonResponse({ configured: true, authenticated: true, username: "reviewer" }),
          );
        }
        if (url.endsWith("/api/admin/sources")) {
          return Promise.resolve(jsonResponse({ items: [source] }));
        }
        if (url.endsWith("/api/admin/ingestion-runs")) {
          return Promise.resolve(jsonResponse({ items: runs }));
        }
        return Promise.reject(new Error(`Unexpected request: ${url}`));
      }),
    );

    await renderRoute("/admin/sources");

    expect(await screen.findByRole("heading", { name: "Check complete" })).toBeInTheDocument();
    const history = screen.getByLabelText("Run history");
    fireEvent.change(history, { target: { value: "CMS-RUN-RUNNING" } });
    expect(screen.getByRole("heading", { name: "Checking official sources" })).toBeInTheDocument();
    expect(screen.getByText("Processing now")).toBeInTheDocument();
    fireEvent.change(history, { target: { value: "CMS-RUN-FAILED" } });
    expect(screen.getByRole("heading", { name: "Complete with errors" })).toBeInTheDocument();
    expect(
      screen.getByText("CMS returned HTTP 503 while retrieving the document.", {
        selector: ".ingestion-item-error",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("1 failed")).toBeInTheDocument();
  });

  it("inspects unresolved normalized fields and requests private clarification", async () => {
    const normalizationSummary = {
      normalization_id: "CMS-NORM-44",
      status: "needs_review",
      parser_version: "cms-labeled-fields-v1",
      measure_candidate_count: 1,
      staged_field_count: 0,
      created_at: "2026-10-26T12:01:00Z",
      created_by: "reviewer",
    };
    const source = {
      source_id: "CMS-PY2026-APP-REQ",
      title: "PY 2026 APP Quality Requirements",
      official_url: "https://www.cms.gov/example/py2026-app.pdf",
      source_format: "pdf",
      is_active: true,
      notes: null,
      created_by: "reviewer",
      created_at: "2026-10-26T12:00:00Z",
      updated_at: "2026-10-26T12:00:00Z",
      deactivated_at: null,
      revision_count: 1,
      latest_revision: {
        revision_id: "CMS-PY2026-APP-REQ-R1",
        revision_number: 1,
        content_hash: "abcdef1234567890",
        source_url: "https://www.cms.gov/example/py2026-app.pdf",
        final_url: "https://www.cms.gov/example/py2026-app.pdf",
        http_status: 200,
        mime_type: "application/pdf",
        byte_length: 2048,
        publication_date: null,
        retrieved_at: "2026-10-26T12:00:00Z",
        last_source_check_at: "2026-10-26T12:00:00Z",
        extraction: {
          extraction_id: "CMS-PY2026-APP-REQ-R1-X1",
          sequence: 1,
          status: "extracted",
          page_count: 4,
          segment_count: 12,
          error: null,
          extractor_version: "pypdf-v1",
          forced: false,
          extracted_at: "2026-10-26T12:00:00Z",
          created_by: "reviewer",
          normalization: normalizationSummary,
        },
      },
      latest_check: null,
    };
    const clarification = {
      clarification_id: "CMS-CLARIFY-1",
      field_candidate_id: "CMS-NFIELD-EXCLUSIONS",
      outcome: "proposed",
      proposed_value: "Patients receiving hospice care are excluded.",
      summary: "One additional official source supports this wording.",
      provider: "openai",
      model: "configured-model",
      prompt_version: "cms-clarification-v1",
      provider_response_id: "response-1",
      created_at: "2026-10-26T12:02:00Z",
      created_by: "reviewer",
      evidence: [
        {
          evidence_id: "CMS-AI-EVID-1",
          source_id: "CMS-CORROBORATING",
          source_revision_id: "CMS-CORROBORATING-R1",
          source_title: "Additional official CMS source",
          official_url: "https://www.cms.gov/example/corroborating.html",
          locator: "HTML section: Exclusions",
          excerpt: "Patients receiving hospice care are excluded.",
          relation: "supports",
          explanation: "The excerpt directly labels the exclusion.",
        },
      ],
    };
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/admin/session")) {
        return Promise.resolve(
          jsonResponse({ configured: true, authenticated: true, username: "reviewer" }),
        );
      }
      if (url.endsWith("/api/admin/sources")) {
        return Promise.resolve(jsonResponse({ items: [source] }));
      }
      if (url.endsWith("/api/admin/ingestion-runs")) {
        return Promise.resolve(jsonResponse({ items: [] }));
      }
      if (url.endsWith("/api/admin/source-normalizations/CMS-NORM-44")) {
        return Promise.resolve(
          jsonResponse({
            ...normalizationSummary,
            extraction_id: "CMS-PY2026-APP-REQ-R1-X1",
            source_id: source.source_id,
            revision_id: source.latest_revision.revision_id,
            candidates: [
              {
                candidate_id: "CMS-NCANDIDATE-1",
                sequence: 1,
                identity_status: "matched",
                measure_id_candidate: "001",
                performance_year_candidate: 2026,
                collection_type_candidate: "ecqm",
                specification_identifier_candidate: "CMS122v14",
                matched_version_id: "CMS-001-PY2026-ECQM",
                issues: ["Unresolved fields: exclusions"],
                fields: [
                  {
                    field_candidate_id: "CMS-NFIELD-EXCLUSIONS",
                    field_name: "exclusions",
                    candidate_value: null,
                    status: "unresolved",
                    segment_sequence: null,
                    evidence_locator: null,
                    source_excerpt: null,
                    staging_status: "unmatched",
                    staged_review_item_id: null,
                    clarifications: [],
                  },
                ],
              },
            ],
          }),
        );
      }
      if (url.endsWith("/CMS-NFIELD-EXCLUSIONS/clarifications") && init?.method === "POST") {
        return Promise.resolve(jsonResponse(clarification));
      }
      return Promise.reject(new Error(`Unexpected request: ${url}`));
    });
    vi.stubGlobal("fetch", fetchMock);

    await renderRoute("/admin/sources");
    fireEvent.click(await screen.findByRole("button", { name: "Inspect candidates" }));
    expect(await screen.findByText("exclusions")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Clarify with AI" }));

    expect(
      await screen.findByText("Patients receiving hospice care are excluded."),
    ).toBeInTheDocument();
    const call = fetchMock.mock.calls.find(([input]) =>
      String(input).endsWith("/CMS-NFIELD-EXCLUSIONS/clarifications"),
    );
    expect(call?.[1]?.headers).toMatchObject({
      "X-CMSQI-Admin-Action": "clarify-source",
    });
  });
});
