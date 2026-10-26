import {
  Outlet,
  createRootRoute,
  createRoute,
  createRouter,
  type RouterHistory,
} from "@tanstack/react-router";

import { AppShell } from "./components/cms/AppShell";
import { parseDemoFilters } from "./features/measures/demo/filters";
import { parseAdminSearch } from "./features/admin/search";
import { DashboardPage } from "./pages/DashboardPage";
import { AdminMeasureDetailPage } from "./pages/AdminMeasureDetailPage";
import { AdminWorkspacePage } from "./pages/AdminWorkspacePage";
import { AdminSourcesPage } from "./pages/AdminSourcesPage";
import { MeasureExplorerPage } from "./pages/MeasureExplorerPage";
import { MeasureDetailPage } from "./pages/MeasureDetailPage";
import { WhatsNewPage } from "./pages/WhatsNewPage";

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

const measureExplorerRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/measures",
  validateSearch: parseDemoFilters,
  component: MeasureExplorerPage,
});

const measureDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/measures/$measureId",
  validateSearch: parseDemoFilters,
  component: MeasureDetailPage,
});

const whatsNewRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/whats-new",
  validateSearch: parseDemoFilters,
  component: WhatsNewPage,
});

const adminRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/admin",
  validateSearch: parseAdminSearch,
  component: AdminWorkspacePage,
});

const adminMeasureDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/admin/measures/$measureId",
  component: AdminMeasureDetailPage,
});

const adminSourcesRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/admin/sources",
  component: AdminSourcesPage,
});

const routeTree = rootRoute.addChildren([
  indexRoute,
  measureExplorerRoute,
  measureDetailRoute,
  whatsNewRoute,
  adminRoute,
  adminSourcesRoute,
  adminMeasureDetailRoute,
]);

export function createAppRouter(history?: RouterHistory) {
  return createRouter({ routeTree, ...(history ? { history } : {}) });
}

export const router = createAppRouter();

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
