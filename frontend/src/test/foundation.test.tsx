import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { fireEvent, render, screen } from "@testing-library/react";
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

describe("visual prototype routes", () => {
  it("renders the interactive dashboard from the root route", async () => {
    await renderRoute("/");

    expect(
      await screen.findByRole("heading", { name: "CMS Quality Intelligence" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/showing 8 of 8 fictional measures/i)).toBeInTheDocument();
    expect(screen.getByText(/fictional prototype data/i)).toBeInTheDocument();
  });

  it("renders measure detail interactions on a stable route", async () => {
    await renderRoute("/measures/PV-103?from=2025&to=2026");

    expect(
      await screen.findByRole("heading", { name: "Breast Cancer Screening" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("Needs re-verification");

    fireEvent.mouseDown(screen.getByRole("tab", { name: "AI Impact" }), {
      button: 0,
      ctrlKey: false,
    });
    fireEvent.click(await screen.findByRole("button", { name: "ACO Quality Manager" }));
    expect(
      await screen.findByText(/coordinate with clinical, reporting, and quality teams/i),
    ).toBeVisible();
  });
});
