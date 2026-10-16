import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { createAppRouter } from "../router";

const summary = {
  measure_id: "DEMO-API-001",
  name: "Fictional API Contract Measure",
  description: "Synthetic backend record for frontend integration testing.",
  performance_years: [2025, 2026],
  change_status: "unknown",
  affected_fields: ["definition"],
  freshness: {
    last_verified_at: null,
    last_source_check_at: "2026-10-01T12:00:00Z",
    verification_status: "partially_verified",
    newer_revision_detected: false,
  },
};

const page = {
  items: [summary],
  pagination: { page: 1, page_size: 100, total_items: 1, total_pages: 1 },
};

const detail = {
  ...summary,
  versions: [
    {
      version_id: "DEMO-VERSION-API-001-2026",
      performance_year: 2026,
      program: "Fictional Quality Program",
      is_program_member: true,
      fields: [
        {
          field: "definition",
          availability: "unresolved",
          value: null,
          evidence: [
            {
              evidence_id: "DEMO-EVIDENCE-API-001",
              source_revision_id: "DEMO-REVISION-API-001",
              document_title: "Fictional Approved Source",
              official_url: "https://example.invalid/demo-source",
              locator: "Fictional section 1",
              excerpt: "Synthetic evidence excerpt for testing only.",
            },
          ],
        },
      ],
    },
  ],
};

async function renderApiRoute(path: string) {
  vi.stubEnv("VITE_DATA_MODE", "api");
  const history = createMemoryHistory({ initialEntries: [path] });
  const router = createAppRouter(history);
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  await router.load();
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

function jsonResponse(value: unknown, status = 200) {
  return new Response(JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("C1 frontend API integration", () => {
  it("loads the Measure Explorer from the public API with URL filters", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(page));
    vi.stubGlobal("fetch", fetchMock);

    await renderApiRoute("/measures?status=unknown&from=2025&to=2026");

    expect(await screen.findByText("Fictional API Contract Measure")).toBeInTheDocument();
    expect(screen.getByText("Showing 1 of 1 measures")).toBeInTheDocument();
    expect(String(fetchMock.mock.calls[0][0])).toContain("change_status=unknown");
    expect(String(fetchMock.mock.calls[0][0])).toContain("from_year=2025");
  });

  it("shows an explicit API error and never substitutes demo fixtures", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Backend offline")));

    await renderApiRoute("/measures?from=2025&to=2026");

    expect(await screen.findByRole("alert")).toHaveTextContent("Backend offline");
    expect(screen.getByText(/No fictional records were substituted/i)).toBeInTheDocument();
    expect(screen.queryByText("Breast Cancer Screening")).not.toBeInTheDocument();
  });

  it("loads a direct detail route with unresolved semantics and M2 boundaries", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        return Promise.resolve(jsonResponse(url.includes("DEMO-API-001?") ? detail : page));
      }),
    );

    await renderApiRoute("/measures/DEMO-API-001?from=2025&to=2026");

    expect(
      await screen.findByRole("heading", { name: "Fictional API Contract Measure" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/unresolved in approved evidence/i)).toBeInTheDocument();
    expect(screen.getByText("Fictional Approved Source")).toBeInTheDocument();

    fireEvent.mouseDown(screen.getByRole("tab", { name: "AI Impact" }), {
      button: 0,
      ctrlKey: false,
    });
    expect(await screen.findByText(/C1 does not call an AI service/i)).toBeVisible();
  });
});
