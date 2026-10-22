import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { createAppRouter } from "../router";

async function renderRoute(path: string) {
  const history = createMemoryHistory({ initialEntries: [path] });
  const router = createAppRouter(history);
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  await router.load();

  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );

  return router;
}

describe("Checkpoint B navigation routes", () => {
  it("keeps the dashboard focused on the comparison ledger", async () => {
    await renderRoute("/");

    expect(
      await screen.findByRole("heading", { name: "Quality, decoded." }),
    ).toBeInTheDocument();
    expect(screen.getByText(/what changed from PY2025 to PY2026/i)).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "What's new" })).not.toBeInTheDocument();
    expect(
      within(screen.getByRole("navigation", { name: "Primary" })).getByRole("link", {
        name: "Home",
      }),
    ).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("loads the Measure Explorer directly and marks its sidebar entry active", async () => {
    await renderRoute("/measures?status=added&from=2025&to=2026");

    expect(
      await screen.findByRole("heading", { name: "Measure Explorer" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByText(/showing 1 of 8 fictional measures/i)).toBeInTheDocument();
    expect(
      within(screen.getByRole("navigation", { name: "Primary" })).getByRole("link", {
        name: "Measures",
      }),
    ).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("loads What's New directly as an independent editorial feed", async () => {
    await renderRoute("/whats-new?from=2026&to=2025");

    expect(await screen.findByRole("heading", { name: "What's new" })).toBeInTheDocument();
    expect(screen.getAllByRole("article")).toHaveLength(3);
    expect(screen.getAllByText("Fictional publication")).toHaveLength(3);
    expect(
      within(screen.getByRole("navigation", { name: "Primary" })).getByRole("link", {
        name: "What's New",
      }),
    ).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("opens Measure Explorer from a dashboard metric with comparison state intact", async () => {
    const router = await renderRoute("/?from=2026&to=2025");

    fireEvent.click(
      await screen.findByRole("button", { name: "View modified measures in Measure Explorer" }),
    );

    await waitFor(() => expect(router.state.location.pathname).toBe("/measures"));
    expect(router.state.location.search).toMatchObject({
      status: "modified",
      from: "2026",
      to: "2025",
    });
    expect(await screen.findByText(/showing 3 of 8 fictional measures/i)).toBeInTheDocument();
  });

  it("preserves filters through measure detail navigation and return", async () => {
    const router = await renderRoute(
      "/measures?status=modified&field=Exclusions&from=2026&to=2025",
    );

    fireEvent.click(await screen.findByRole("link", { name: "PV-103" }));

    await waitFor(() => expect(router.state.location.pathname).toBe("/measures/PV-103"));
    expect(router.state.location.search).toMatchObject({
      status: "modified",
      field: "Exclusions",
      from: "2026",
      to: "2025",
    });
    expect(
      await screen.findByRole("heading", { name: "Breast Cancer Screening" }),
    ).toBeInTheDocument();

    fireEvent.click(
      within(screen.getByRole("navigation", { name: "Breadcrumb" })).getByRole("link", {
        name: "Measures",
      }),
    );
    await waitFor(() => expect(router.state.location.pathname).toBe("/measures"));
    expect(router.state.location.search).toMatchObject({
      status: "modified",
      field: "Exclusions",
      from: "2026",
      to: "2025",
    });
  });

  it("renders measure detail interactions on a stable direct route", async () => {
    await renderRoute("/measures/PV-103?from=2025&to=2026");

    expect(
      await screen.findByRole("heading", { name: "Breast Cancer Screening" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("Needs re-verification");
    expect(
      within(screen.getByRole("navigation", { name: "Primary" })).getByRole("link", {
        name: "Measures",
      }),
    ).toHaveAttribute(
      "aria-current",
      "page",
    );

    fireEvent.mouseDown(screen.getByRole("tab", { name: "AI Impact" }), {
      button: 0,
      ctrlKey: false,
    });
    fireEvent.click(await screen.findByRole("button", { name: "ACO Quality Manager" }));
    expect(
      await screen.findByText(/coordinate with clinical, reporting, and quality teams/i),
    ).toBeVisible();
  });

  it("opens the protected admin workspace from the workspace switch", async () => {
    const router = await renderRoute("/");

    fireEvent.click(await screen.findByRole("radio", { name: "Admin" }));

    await waitFor(() => expect(router.state.location.pathname).toBe("/admin"));
    expect(screen.getByText("Review workspace")).toBeInTheDocument();
    expect(screen.getByText(/private source-backed drafts/)).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Admin" })).toHaveAttribute("aria-checked", "true");
  });
});
