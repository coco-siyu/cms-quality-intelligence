import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { fireEvent, render, screen, within } from "@testing-library/react";
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

const changePage = {
  items: [
    {
      measure_id: summary.measure_id,
      measure_name: summary.name,
      program: "Fictional Quality Program",
      collection_type: "program_roster",
      from_year: 2025,
      to_year: 2026,
      status: "modified",
      evidence_status: "verified",
      approved_at: "2026-10-14T12:00:00Z",
      published_at: "2026-10-16T12:00:00Z",
      fields: [
        {
          field: "definition",
          status: "modified",
          from_availability: "available",
          to_availability: "available",
          from_value: "Fictional 2025 definition.",
          to_value: "Fictional 2026 definition.",
          evidence: [
            {
              evidence_id: "DEMO-CHANGE-EVIDENCE-2025",
              source_revision_id: "DEMO-CHANGE-REVISION-2025",
              document_title: "Fictional 2025 Official Source",
              official_url: "https://example.invalid/fictional-2025-source",
              publication_date: "2025-01-15",
              locator: "Fictional page 5",
              excerpt: "Fictional source wording for the 2025 definition.",
              side: "from_version",
            },
            {
              evidence_id: "DEMO-CHANGE-EVIDENCE-2026",
              source_revision_id: "DEMO-CHANGE-REVISION-2026",
              document_title: "Fictional 2026 Official Source",
              official_url: "https://example.invalid/fictional-2026-source",
              publication_date: "2026-01-20",
              locator: "Fictional page 6",
              excerpt: "Fictional source wording for the 2026 definition.",
              side: "to_version",
            },
          ],
        },
        {
          field: "calculation_logic",
          status: "wording_only",
          from_availability: "available",
          to_availability: "available",
          from_value: "Fictional calculation wording for 2025.",
          to_value: "Rephrased fictional calculation wording for 2026.",
          evidence: [],
        },
        {
          field: "numerator",
          status: "unknown",
          from_availability: "unavailable",
          to_availability: "unresolved",
          from_value: null,
          to_value: null,
          evidence: [],
        },
      ],
    },
  ],
  pagination: { page: 1, page_size: 100, total_items: 1, total_pages: 1 },
};

const performanceYears = {
  years: [2024, 2025, 2026],
  default_from_year: 2025,
  default_to_year: 2026,
};

const navigation = {
  measure_id: summary.measure_id,
  position: 1,
  total_items: 2,
  previous_measure_id: null,
  next_measure_id: "DEMO-API-002",
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

const rosterEvidence = [
  {
    evidence_id: "CMS-EVIDENCE-001-2025-1",
    source_revision_id: "CMS-PFS-2025-FINAL-FACT-SHEET-R1",
    document_title: "CY 2025 PFS Final Rule — Shared Savings Program Provisions",
    official_url:
      "https://www.cms.gov/newsroom/fact-sheets/calendar-year-cy-2025-medicare-physician-fee-schedule-final-rule-cms-1807-f-medicare-shared-savings",
    locator: "Table 1",
    excerpt: "Official cross-year roster evidence for Quality ID 001.",
  },
  {
    evidence_id: "CMS-EVIDENCE-001-2025-2",
    source_revision_id: "CMS-APPPLUS-PY2025-QPS-R1",
    document_title: "PY 2025 Quality Performance Standard",
    official_url:
      "https://www.cms.gov/files/document/performance-year-2025-40th-percentile-mips-quality-performance-category-score.pdf",
    locator: "PY2025 measure roster",
    excerpt: "Official year-specific roster evidence for Quality ID 001.",
  },
];

const sourceBackedDetail = {
  measure_id: "001",
  name: "Diabetes: Glycemic Status Assessment Greater Than 9%",
  description:
    "Official program-year roster membership is verified; detailed specification fields remain under review.",
  performance_years: [2025, 2026],
  change_status: "unknown",
  affected_fields: [],
  freshness: {
    last_verified_at: "2026-10-16T12:00:00Z",
    last_source_check_at: "2026-10-16T12:00:00Z",
    verification_status: "verified",
    newer_revision_detected: false,
  },
  versions: [2025, 2026].map((year) => ({
    version_id: `CMS-APPPLUS-001-PY${year}-ROSTER-R1`,
    performance_year: year,
    program: "Medicare Shared Savings Program — APP Plus",
    is_program_member: true,
    fields: [
      {
        field: "measure_set",
        availability: "available",
        value: `Member of the PY${year} MSSP APP Plus quality measure set.`,
        evidence: rosterEvidence.map((reference, index) => ({
          ...reference,
          evidence_id: `CMS-EVIDENCE-001-${year}-${index + 1}`,
        })),
      },
    ],
  })),
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
  return router;
}

function jsonResponse(value: unknown, status = 200) {
  return new Response(JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function apiFetch(input: RequestInfo | URL) {
  const url = String(input);
  if (url.includes("/api/performance-years")) return Promise.resolve(jsonResponse(performanceYears));
  if (url.includes(`/api/changes/${summary.measure_id}?`)) {
    return Promise.resolve(jsonResponse(changePage.items[0]));
  }
  if (url.includes("/api/changes?")) return Promise.resolve(jsonResponse(changePage));
  if (url.includes("/navigation")) return Promise.resolve(jsonResponse(navigation));
  if (url.includes(`/api/measures/${summary.measure_id}?`)) return Promise.resolve(jsonResponse(detail));
  return Promise.resolve(jsonResponse(page));
}

function requestedUrl(fetchMock: ReturnType<typeof vi.fn>, fragment: string) {
  const call = fetchMock.mock.calls.find(([input]) => String(input).includes(fragment));
  expect(call).toBeDefined();
  return String(call?.[0]);
}

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("public frontend API integration", () => {
  it("uses published API records on the redesigned dashboard", async () => {
    const fetchMock = vi.fn(apiFetch);
    vi.stubGlobal("fetch", fetchMock);

    await renderApiRoute("/?from=2025&to=2026");

    expect(await screen.findByRole("heading", { name: "Quality, decoded." })).toBeInTheDocument();
    expect(screen.getByText(/of 1 published measures in PY2026/i)).toBeInTheDocument();
    expect(screen.getByText(/Published performance-year comparison records/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Evidence-backed changes" })).toBeInTheDocument();
    const changeRow = screen.getByRole("listitem");
    expect(changeRow).toHaveTextContent("Fictional API Contract Measure");
    expect(within(changeRow).getByRole("link")).toHaveAttribute(
      "href",
      expect.stringContaining("/measures/DEMO-API-001"),
    );
    expect(
      within(screen.getByRole("button", { name: "View modified measures in Measure Explorer" }))
        .getByText("1"),
    ).toBeInTheDocument();
    expect(screen.queryByText("Fictional data")).not.toBeInTheDocument();
    expect(screen.queryByText("Breast Cancer Screening")).not.toBeInTheDocument();
    expect(requestedUrl(fetchMock, "/api/measures?")).toContain("from_year=2025");
    const changesUrl = requestedUrl(fetchMock, "/api/changes?");
    expect(changesUrl).toContain("collection_type=program_roster");
    expect(changesUrl).toContain("from_year=2025");
    expect(screen.getAllByRole("option", { name: "PY2024" })).toHaveLength(2);

    fireEvent.change(screen.getByRole("searchbox", { name: "Search published changes" }), {
      target: { value: "no matching measure" },
    });
    expect(screen.getByText("No published changes match this search.")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Clear search" }));
    expect(screen.getByRole("listitem")).toHaveTextContent("Fictional API Contract Measure");
  });

  it("shows an honest dashboard state when no verified comparisons are public", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/api/performance-years")) {
          return Promise.resolve(jsonResponse(performanceYears));
        }
        if (url.includes("/api/changes?")) {
          return Promise.resolve(
            jsonResponse({
              items: [],
              pagination: { page: 1, page_size: 100, total_items: 0, total_pages: 0 },
            }),
          );
        }
        return Promise.resolve(jsonResponse(page));
      }),
    );

    await renderApiRoute("/?from=2025&to=2026");

    expect(await screen.findByText("No verified change records are public yet.")).toBeVisible();
    expect(screen.getByText(/only after both year versions and their evidence/i)).toBeVisible();
    expect(screen.queryByText("Breast Cancer Screening")).not.toBeInTheDocument();
  });

  it("uses the API change direction without reversing added and removed statuses twice", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/api/performance-years")) {
          return Promise.resolve(jsonResponse(performanceYears));
        }
        if (url.includes("/api/changes?")) {
          return Promise.resolve(
            jsonResponse({
              ...changePage,
              items: [{ ...changePage.items[0], from_year: 2026, to_year: 2025, status: "added" }],
            }),
          );
        }
        return Promise.resolve(jsonResponse(page));
      }),
    );

    await renderApiRoute("/?from=2026&to=2025");
    await screen.findByRole("heading", { name: "Evidence-backed changes" });

    expect(
      within(screen.getByRole("button", { name: "View added measures in Measure Explorer" }))
        .getByText("1"),
    ).toBeVisible();
    expect(
      within(screen.getByRole("button", { name: "View removed measures in Measure Explorer" }))
        .getByText("0"),
    ).toBeVisible();
  });

  it("renders a chronological public What's New feed with distinct source and approval dates", async () => {
    const fetchMock = vi.fn(apiFetch);
    vi.stubGlobal("fetch", fetchMock);

    await renderApiRoute("/whats-new?from=2025&to=2026");

    expect(
      await screen.findByRole("heading", {
        name: "Approved changes published for Fictional API Contract Measure",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("CMS source dates")).toBeInTheDocument();
    expect(screen.getByText("Jan 15, 2025 · Jan 20, 2026")).toBeInTheDocument();
    expect(screen.getByText("Internal approval")).toBeInTheDocument();
    expect(screen.getByText("Oct 14, 2026")).toBeInTheDocument();
    expect(screen.getByText("Public update")).toBeInTheDocument();
    expect(screen.getByText("Oct 16, 2026")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /View approved comparison/ })).toHaveAttribute(
      "href",
      expect.stringContaining(`/measures/${summary.measure_id}`),
    );
    expect(requestedUrl(fetchMock, "/api/performance-years")).toContain("performance-years");
    expect(requestedUrl(fetchMock, "/api/changes?")).toContain("from_year=2025");
  });

  it("loads the Measure Explorer from the public API with URL filters", async () => {
    const fetchMock = vi.fn(apiFetch);
    vi.stubGlobal("fetch", fetchMock);

    await renderApiRoute("/measures?status=unknown&from=2025&to=2026");

    expect(await screen.findByText("Fictional API Contract Measure")).toBeInTheDocument();
    expect(screen.getByText("Showing 1 of 1 measures")).toBeInTheDocument();
    const listUrl = requestedUrl(fetchMock, "/api/measures?");
    expect(listUrl).toContain("change_status=unknown");
    expect(listUrl).toContain("from_year=2025");
  });

  it("shows an explicit API error and never substitutes demo fixtures", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) =>
        String(input).includes("/api/performance-years")
          ? Promise.resolve(jsonResponse(performanceYears))
          : Promise.reject(new Error("Backend offline")),
      ),
    );

    await renderApiRoute("/measures?from=2025&to=2026");

    expect(await screen.findByRole("alert")).toHaveTextContent("Backend offline");
    expect(screen.getByText(/No fictional records were substituted/i)).toBeInTheDocument();
    expect(screen.queryByText("Breast Cancer Screening")).not.toBeInTheDocument();
  });

  it("loads an evidence-backed side-by-side comparison on a direct detail route", async () => {
    const fetchMock = vi.fn(apiFetch);
    vi.stubGlobal("fetch", fetchMock);

    await renderApiRoute("/measures/DEMO-API-001?from=2025&to=2026");

    expect(
      await screen.findByRole("heading", { name: "Fictional API Contract Measure" }),
    ).toBeInTheDocument();
    expect(await screen.findByText("Approved field comparison")).toBeInTheDocument();
    expect(screen.getByText("Fictional 2025 definition.")).toBeInTheDocument();
    expect(screen.getByText("Fictional 2026 definition.")).toBeInTheDocument();
    expect(screen.getByText("Wording only")).toBeVisible();
    expect(
      screen.getByText("This field is explicitly unavailable in the approved public record."),
    ).toBeVisible();
    expect(screen.getByText("The approved evidence does not resolve this field.")).toBeVisible();
    expect(screen.getByText("Fictional 2025 Official Source")).toHaveAttribute(
      "href",
      "https://example.invalid/fictional-2025-source",
    );
    expect(screen.getByText("Fictional 2026 Official Source")).toHaveAttribute(
      "href",
      "https://example.invalid/fictional-2026-source",
    );
    expect(screen.getByText("1 of 2")).toBeInTheDocument();
    expect(
      decodeURIComponent(
        screen.getByRole("link", { name: /Next.*DEMO-API-002/i }).getAttribute("href") ?? "",
      ),
    ).toContain('from="2025"');

    const comparisonUrl = requestedUrl(fetchMock, `/api/changes/${summary.measure_id}?`);
    expect(comparisonUrl).toContain("program=Fictional+Quality+Program");
    expect(comparisonUrl).toContain("collection_type=program_roster");
    expect(comparisonUrl).toContain("from_year=2025");
    expect(comparisonUrl).toContain("to_year=2026");

    fireEvent.mouseDown(screen.getByRole("tab", { name: "AI Impact" }), {
      button: 0,
      ctrlKey: false,
    });
    expect(await screen.findByText(/C1 does not call an AI service/i)).toBeVisible();
  });

  it("keeps list filters in server-authoritative detail navigation", async () => {
    const fetchMock = vi.fn(apiFetch);
    vi.stubGlobal("fetch", fetchMock);

    await renderApiRoute(
      "/measures/DEMO-API-001?q=follow-up&status=unknown&year=2026&from=2025&to=2026",
    );

    const nextLink = await screen.findByRole("link", { name: /Next.*DEMO-API-002/i });
    const href = decodeURIComponent(nextLink.getAttribute("href") ?? "");
    expect(href).toContain("q=follow-up");
    expect(href).toContain("status=unknown");
    expect(href).toContain('year="2026"');

    const navigationUrl = requestedUrl(fetchMock, "/navigation?");
    expect(navigationUrl).toContain("q=follow-up");
    expect(navigationUrl).toContain("change_status=unknown");
    expect(navigationUrl).toContain("performance_year=2026");
  });

  it("reconciles unsupported direct-route years to API defaults", async () => {
    const fetchMock = vi.fn(apiFetch);
    vi.stubGlobal("fetch", fetchMock);

    const router = await renderApiRoute("/measures?from=2030&to=2031&year=2030");

    expect(await screen.findByText("Fictional API Contract Measure")).toBeInTheDocument();
    await vi.waitFor(() => {
      expect(router.state.location.search).toMatchObject({
        from: "2025",
        to: "2026",
        year: "all",
      });
    });
  });

  it("renders source-backed seeded roster evidence without exposing draft fields", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/api/performance-years")) {
          return Promise.resolve(jsonResponse(performanceYears));
        }
        if (url.includes("/navigation")) {
          return Promise.resolve(
            jsonResponse({
              measure_id: "001",
              position: 1,
              total_items: 8,
              previous_measure_id: null,
              next_measure_id: "112",
            }),
          );
        }
        if (url.includes("/api/changes/001?")) {
          return Promise.resolve(
            jsonResponse({ code: "comparison_not_found", message: "Not found", details: [] }, 404),
          );
        }
        return Promise.resolve(jsonResponse(sourceBackedDetail));
      }),
    );

    await renderApiRoute("/measures/001?from=2025&to=2026");

    expect(
      await screen.findByRole("heading", {
        name: "Diabetes: Glycemic Status Assessment Greater Than 9%",
      }),
    ).toBeInTheDocument();
    expect(
      await screen.findByText("No approved comparison is public for this year pair."),
    ).toBeVisible();
    expect(screen.getByText("Member of the PY2025 MSSP APP Plus quality measure set.")).toBeVisible();
    expect(screen.getByText("Member of the PY2026 MSSP APP Plus quality measure set.")).toBeVisible();
    expect(screen.getAllByRole("link", { name: /Open source/i })).toHaveLength(4);
    expect(screen.queryByText(/Patients 18-75/i)).not.toBeInTheDocument();
  });

  it("does not request a comparison when the selected years are the same", async () => {
    const fetchMock = vi.fn(apiFetch);
    vi.stubGlobal("fetch", fetchMock);

    await renderApiRoute("/measures/DEMO-API-001?from=2025&to=2025");

    expect(await screen.findByText("Choose two different performance years.")).toBeVisible();
    expect(
      fetchMock.mock.calls.some(([input]) =>
        String(input).includes(`/api/changes/${summary.measure_id}?`),
      ),
    ).toBe(false);
  });
});
