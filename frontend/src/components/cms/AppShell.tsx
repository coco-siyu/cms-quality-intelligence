import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useRouterState, useSearch } from "@tanstack/react-router";
import {
  ArrowRight,
  ChevronsLeft,
  ChevronsRight,
  Database,
  Home,
  Menu,
  Newspaper,
  Search,
  ShieldCheck,
} from "lucide-react";

import { Dialog, DialogContent, DialogTitle } from "../ui/dialog";
import { FICTIONAL_DATA_NOTICE } from "../../features/measures/demo/fixtures";
import { parseDemoFilters } from "../../features/measures/demo/filters";
import type { DemoFilters } from "../../features/measures/demo/types";
import { getDataMode } from "../../features/measures/dataMode";
import { usePerformanceYears } from "../../features/measures/api/queries";

const primaryNavigation = [
  { to: "/", label: "Home", icon: Home },
  { to: "/measures", label: "Measures", icon: Search },
  { to: "/whats-new", label: "What's New", icon: Newspaper },
] as const;

function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <span className="site-logo">
      <span className="site-logo-mark" aria-hidden="true">
        <span />
        <span />
        <span />
        <span />
      </span>
      {!compact && (
        <span className="site-logo-name">
          CMS Quality
          <br />
          Intelligence
        </span>
      )}
    </span>
  );
}

function SidebarBody({
  collapsed,
  filters,
  path,
  onNavigate,
}: {
  collapsed: boolean;
  filters: DemoFilters;
  path: string;
  onNavigate?: () => void;
}) {
  const navigate = useNavigate();
  const workspace = path.startsWith("/admin") ? "admin" : "public";
  const isActive = (to: string) => (to === "/" ? path === "/" : path.startsWith(to));

  return (
    <>
      <nav className="site-navigation" aria-label="Primary">
        {primaryNavigation.map((item) => {
          const active = isActive(item.to);
          return (
            <Link
              key={item.to}
              to={item.to}
              search={filters}
              onClick={onNavigate}
              aria-current={active ? "page" : undefined}
              aria-label={item.label}
              title={collapsed ? item.label : undefined}
              className={`site-nav-link ${active ? "active" : ""}`}
            >
              <item.icon aria-hidden="true" />
              {!collapsed && <span>{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      <div className="workspace-divider" />
      {!collapsed && (
        <section className="workspace-switch" aria-label="Workspace">
          <p>Workspace</p>
          <div role="radiogroup" aria-label="Workspace selection">
            <button
              type="button"
              role="radio"
              aria-checked={workspace === "public"}
              onClick={() => {
                void navigate({ to: "/", search: filters });
                onNavigate?.();
              }}
            >
              Public
            </button>
            <button
              type="button"
              role="radio"
              aria-checked={workspace === "admin"}
              onClick={() => {
                void navigate({ to: "/admin", search: {} });
                onNavigate?.();
              }}
            >
              Admin
            </button>
          </div>
          {workspace === "admin" && (
            <div className="workspace-placeholder" role="status">
              <ShieldCheck aria-hidden="true" />
              <span>
                <strong>Review workspace</strong>
                <small>Authenticated access to private source-backed drafts.</small>
              </span>
            </div>
          )}
        </section>
      )}
    </>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const navigate = useNavigate();
  const rawSearch = useSearch({ strict: false });
  const filters = parseDemoFilters(rawSearch);
  const path = useRouterState({ select: (state) => state.location.pathname });
  const dataMode = getDataMode();
  const isAdmin = path.startsWith("/admin");
  const performanceYearsQuery = usePerformanceYears(dataMode === "api" && !isAdmin);
  const performanceYears =
    dataMode === "demo"
      ? [2025, 2026]
      : (performanceYearsQuery.data?.years ??
        [...new Set([Number(filters.from), Number(filters.to)])].filter(Number.isInteger));

  const updateComparison = useCallback((values: Partial<DemoFilters>) => {
    const nextSearch = { ...filters, ...values };

    if (path === "/") {
      void navigate({ to: "/", search: nextSearch, replace: true });
    } else if (path === "/measures") {
      void navigate({ to: "/measures", search: nextSearch, replace: true });
    } else if (path === "/whats-new") {
      void navigate({ to: "/whats-new", search: nextSearch, replace: true });
    } else if (path.startsWith("/measures/")) {
      void navigate({
        to: "/measures/$measureId",
        params: { measureId: decodeURIComponent(path.slice("/measures/".length)) },
        search: nextSearch,
        replace: true,
      });
    }
  }, [filters, navigate, path]);

  useEffect(() => {
    const available = performanceYearsQuery.data;
    if (dataMode !== "api" || isAdmin || !available) return;

    const allowedYears = new Set(available.years.map(String));
    const from = allowedYears.has(filters.from)
      ? filters.from
      : String(available.default_from_year);
    const to = allowedYears.has(filters.to) ? filters.to : String(available.default_to_year);
    const year = filters.year === "all" || allowedYears.has(filters.year) ? filters.year : "all";

    if (from !== filters.from || to !== filters.to || year !== filters.year) {
      updateComparison({ from, to, year });
    }
  }, [dataMode, filters.from, filters.to, filters.year, isAdmin, performanceYearsQuery.data, updateComparison]);

  return (
    <div className={`site-layout ${collapsed ? "site-sidebar-collapsed" : ""}`}>
      <aside className="site-sidebar">
        <Link to="/" search={filters} aria-label="CMS Quality Intelligence home">
          <Logo compact={collapsed} />
        </Link>
        <SidebarBody collapsed={collapsed} filters={filters} path={path} />
        <button
          type="button"
          className="sidebar-collapse"
          onClick={() => setCollapsed((value) => !value)}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <ChevronsRight /> : <ChevronsLeft />}
          {!collapsed && <span>Collapse</span>}
        </button>
      </aside>

      <div className="site-content">
        <header className="site-header">
          <button
            type="button"
            className="mobile-menu-trigger"
            onClick={() => setMobileMenuOpen(true)}
            aria-label="Open menu"
          >
            <Menu />
          </button>
          <span className="mobile-logo">
            <Logo compact />
          </span>

          {!isAdmin && <div className="header-comparison" aria-label="Performance-year comparison">
            <span>Compare</span>
            <label>
              <span className="sr-only">Baseline year</span>
              <select
                aria-label="Baseline year"
                value={filters.from}
                onChange={(event) => updateComparison({ from: event.target.value })}
              >
                {performanceYears.map((year) => (
                  <option key={year} value={year}>PY{year}</option>
                ))}
              </select>
            </label>
            <ArrowRight aria-hidden="true" />
            <label>
              <span className="sr-only">Comparison year</span>
              <select
                aria-label="Comparison year"
                value={filters.to}
                onChange={(event) => updateComparison({ to: event.target.value })}
              >
                {performanceYears.map((year) => (
                  <option key={year} value={year}>PY{year}</option>
                ))}
              </select>
            </label>
          </div>}
          <span className={`data-mode-pill ${isAdmin ? "private" : dataMode}`}>
            {isAdmin ? "Private drafts" : dataMode === "demo" ? "Demo data" : "Published API"}
          </span>
        </header>

        <main className="site-main">{children}</main>
        <footer className="site-footer">
          <span>
            {isAdmin
              ? "Protected review workspace. Draft records are excluded from public API responses."
              : dataMode === "demo"
              ? FICTIONAL_DATA_NOTICE
              : "Independent intelligence interface. Confirm source freshness and evidence before operational use."}
          </span>
          <a
            href="https://www.cms.gov/medicare/payment/fee-for-service-providers/shared-savings-program-ssp-acos"
            target="_blank"
            rel="noreferrer"
          >
            CMS Shared Savings Program
          </a>
        </footer>
      </div>

      <nav className={`mobile-bottom-navigation ${isAdmin ? "admin-mobile-navigation" : ""}`} aria-label="Mobile">
        {(isAdmin
          ? [
              { to: "/admin", label: "Review", icon: ShieldCheck },
              { to: "/admin/sources", label: "Sources", icon: Database },
              { to: "/", label: "Public site", icon: Home },
            ] as const
          : primaryNavigation
        ).map((item) => {
          const active =
            item.to === "/" || item.to === "/admin"
              ? path === item.to
              : path.startsWith(item.to);
          return (
            <Link
              key={item.to}
              to={item.to}
              search={item.to === "/admin" ? {} : filters}
              aria-current={active ? "page" : undefined}
              aria-label={item.label}
              className={active ? "active" : ""}
            >
              <item.icon aria-hidden="true" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <Dialog open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
        <DialogContent className="mobile-navigation-dialog">
          <DialogTitle className="mobile-dialog-title">
            <Logo />
          </DialogTitle>
          <SidebarBody
            collapsed={false}
            filters={filters}
            path={path}
            onNavigate={() => setMobileMenuOpen(false)}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
}
