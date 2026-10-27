import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { createAppRouter } from "../router";

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
