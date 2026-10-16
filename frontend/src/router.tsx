import {
  Outlet,
  createRootRoute,
  createRoute,
  createRouter,
  type RouterHistory,
} from "@tanstack/react-router";

import { AppShell } from "./components/cms/AppShell";
import { parseDemoFilters } from "./features/measures/demo/filters";
import { DashboardPage } from "./pages/DashboardPage";
import { MeasureDetailPage } from "./pages/MeasureDetailPage";

const rootRoute = createRootRoute({
  component: () => (
    <AppShell>
      <Outlet />
    </AppShell>
  ),
  notFoundComponent: () => (
    <div className="empty-state">
      <h1>Page not found</h1>
      <p>The requested prototype page does not exist.</p>
    </div>
  ),
});

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  validateSearch: parseDemoFilters,
  component: DashboardPage,
});

const measureDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/measures/$measureId",
  validateSearch: parseDemoFilters,
  component: MeasureDetailPage,
});

const routeTree = rootRoute.addChildren([indexRoute, measureDetailRoute]);

export function createAppRouter(history?: RouterHistory) {
  return createRouter({ routeTree, ...(history ? { history } : {}) });
}

export const router = createAppRouter();

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
