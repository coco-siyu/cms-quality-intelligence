import { useState } from "react";
import { Link, useNavigate, useRouterState, useSearch } from "@tanstack/react-router";
import {
  ArrowRight,
  ExternalLink,
  LayoutDashboard,
  ListFilter,
  Newspaper,
  PanelLeftClose,
  PanelLeftOpen,
  Search,
  ShieldCheck,
} from "lucide-react";

import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { FICTIONAL_DATA_NOTICE } from "../../features/measures/demo/fixtures";
import { parseDemoFilters } from "../../features/measures/demo/filters";
import { FilterSelect } from "./shared";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const search = useSearch({ strict: false });
  const filters = parseDemoFilters(search);
  const path = useRouterState({ select: (state) => state.location.pathname });

  function update(values: Partial<typeof filters>) {
    void navigate({
      to: "/",
      search: { ...filters, ...values },
      replace: path === "/",
    });
  }

  const years = [
    { value: "2025", label: "PY2025" },
    { value: "2026", label: "PY2026" },
  ];

  return (
    <div className={`app-layout ${collapsed ? "sidebar-collapsed" : ""}`}>
      <aside className="app-sidebar">
        <Link to="/" search={filters} className="brand" aria-label="CMS Quality Intelligence home">
          <svg
            className="brand-logo"
            width="32"
            height="32"
            viewBox="0 0 32 32"
            fill="none"
            aria-hidden="true"
          >
            <circle cx="9" cy="6" r="3.5" className="logo-hollow" />
            <path d="M9 10v12" className="logo-dashed" />
            <circle cx="9" cy="26" r="3.5" className="logo-blue" />
            <circle cx="23" cy="6" r="3.5" className="logo-ink" />
            <path d="M23 10v12" className="logo-line" />
            <circle cx="23" cy="26" r="3.5" className="logo-ink" />
          </svg>
          <span className="brand-name">
            CMS Quality
            <br />
            Intelligence
          </span>
          <span className="brand-subtitle">Medicare Shared Savings Program</span>
        </Link>

        <nav aria-label="Primary">
          <Button
            asChild
            variant="ghost"
            className={`sidebar-link ${path === "/" ? "active" : ""}`}
            title="Dashboard"
          >
            <Link to="/" search={filters}>
              <LayoutDashboard />
              <span>Dashboard</span>
            </Link>
          </Button>
          <Button
            asChild
            variant="ghost"
            className={`sidebar-link ${path !== "/" ? "active" : ""}`}
            title="Measure Explorer"
          >
            <Link to="/" search={filters} hash="measures">
              <ListFilter />
              <span>Measure Explorer</span>
            </Link>
          </Button>
          <Button asChild variant="ghost" className="sidebar-link" title="What's new">
            <Link to="/" search={filters} hash="whats-new">
              <Newspaper />
              <span>What&apos;s New</span>
            </Link>
          </Button>
        </nav>

        <div className="sidebar-bottom">
          <ShieldCheck size={17} />
          <span>
            Evidence before insight.
            <br />
            <small>MSSP / APP Plus</small>
          </span>
        </div>
      </aside>

      <main className="app-main">
        <div className="topbar">
          <Button
            variant="ghost"
            size="icon"
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            onClick={() => setCollapsed((value) => !value)}
          >
            {collapsed ? <PanelLeftOpen /> : <PanelLeftClose />}
          </Button>
          <div className="global-search">
            <Search size={16} />
            <Input
              type="search"
              aria-label="Search all measure attributes"
              placeholder="Search fictional measures or IDs"
              value={filters.q}
              onChange={(event) => update({ q: event.target.value })}
            />
          </div>
          <div className="compare-control">
            <span>Compare</span>
            <FilterSelect
              label="Baseline year"
              value={filters.from}
              options={years}
              onChange={(from) => update({ from })}
            />
            <ArrowRight size={14} />
            <FilterSelect
              label="Comparison year"
              value={filters.to}
              options={years}
              onChange={(to) => update({ to })}
            />
          </div>
          <span className="demo-mode">Prototype mode</span>
        </div>

        <div className="page-sheet">
          {children}
          <footer className="sheet-footer">
            <span>{FICTIONAL_DATA_NOTICE}</span>
            <a
              href="https://www.cms.gov/medicare/payment/fee-for-service-providers/shared-savings-program-ssp-acos"
              target="_blank"
              rel="noreferrer"
            >
              CMS Shared Savings Program <ExternalLink size={12} />
            </a>
          </footer>
        </div>
      </main>
    </div>
  );
}
