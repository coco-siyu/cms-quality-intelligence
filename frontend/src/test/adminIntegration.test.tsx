import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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
    expect(screen.getByText(/This checkpoint is read-only/i)).toBeInTheDocument();
    expect(screen.queryByText("DEMO-001")).not.toBeInTheDocument();
    await waitFor(() => {
      expect(fetchMock.mock.calls.every((call) => call[1]?.credentials === "include")).toBe(true);
    });
  });

  it("loads a private measure directly with source provenance", async () => {
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
          candidates: [
            {
              review_item_id: "CMS-001-PY2025-ECQM-definition",
              field_name: "definition",
              candidate_value: "Candidate definition requiring human review.",
              extraction_status: "source_extracted",
              evidence_locator: "Page 4",
              review_decision: "pending",
              reviewed_value: null,
              reviewer_name: null,
              reviewed_at: null,
              reviewer_notes: null,
              source_id: "CMS-SOURCE-001",
              source_revision_id: "CMS-SOURCE-001-R1",
              source_title: "Official CMS specification",
              official_url: "https://www.cms.gov/example",
              source_content_hash: "hash",
            },
          ],
        },
      ],
    };
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/api/admin/session")) {
          return Promise.resolve(
            jsonResponse({ configured: true, authenticated: true, username: "reviewer" }),
          );
        }
        if (url.endsWith("/api/admin/measures/001")) return Promise.resolve(jsonResponse(detail));
        return Promise.reject(new Error(`Unexpected request: ${url}`));
      }),
    );

    await renderRoute("/admin/measures/001");

    expect(
      await screen.findByRole("heading", {
        name: "Diabetes: Glycemic Status Assessment Greater Than 9%",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("Private draft")).toBeInTheDocument();
    fireEvent.click(screen.getByText("definition"));
    expect(screen.getByText("Candidate definition requiring human review.")).toBeVisible();
    expect(screen.getByRole("link", { name: /Official CMS specification/ })).toHaveAttribute(
      "href",
      "https://www.cms.gov/example",
    );
  });
});
