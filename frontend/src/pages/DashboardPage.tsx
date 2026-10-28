import { Link, useNavigate, useSearch } from "@tanstack/react-router";
import { ArrowRight, Newspaper, Rows3 } from "lucide-react";

import { ChangeLedger } from "../components/cms/ChangeLedger";
import { HeroCollage } from "../components/cms/HeroCollage";
import { DemoBadge, ErrorState, LoadingState } from "../components/cms/shared";
import { apiSummaryToMeasure } from "../features/measures/api/adapters";
import { useApiMeasureList, usePerformanceYears } from "../features/measures/api/queries";
import { getDataMode, type DataMode } from "../features/measures/dataMode";
import { parseDemoFilters } from "../features/measures/demo/filters";
import { useDemoMeasureList } from "../features/measures/demo/queries";
import type { DemoFilters, DemoMeasure } from "../features/measures/demo/types";

function DashboardContent({
  filters,
  measures,
  performanceYears,
  dataMode,
}: {
  filters: DemoFilters;
  measures: DemoMeasure[];
  performanceYears: number[];
  dataMode: DataMode;
}) {
  const navigate = useNavigate({ from: "/" });
  const measuresInComparisonYear = measures.filter((measure) =>
    measure.years.includes(Number(filters.to)),
  ).length;

  function updateComparison(values: Partial<DemoFilters>) {
    void navigate({ search: { ...filters, ...values }, replace: true });
  }

  function openStatus(status: string) {
    void navigate({
      to: "/measures",
      search: { ...filters, status },
    });
  }

  return (
    <div className="visual-page home-page">
      <section className="home-hero">
        <div className="home-hero-copy">
          <p className="home-eyebrow">CMS Quality Intelligence</p>
          <h1>Quality, decoded.</h1>
          <p className="home-deck">
            Understand what changed in CMS quality measures—and why it matters.
          </p>
          <div className="home-actions">
            <Link to="/measures" search={filters} className="primary-action">
              Explore changes <ArrowRight aria-hidden="true" />
            </Link>
            <span>MSSP / APP Plus · PY{filters.from}–PY{filters.to}</span>
          </div>
        </div>
        <HeroCollage />
      </section>

      <section className="comparison-band" aria-label="Comparison summary">
        <div className="year-card surface-card">
          <p className="card-kicker">Compare years</p>
          <div>
            <label>
              <span className="sr-only">Dashboard baseline year</span>
              <select
                aria-label="Dashboard baseline year"
                value={filters.from}
                onChange={(event) => updateComparison({ from: event.target.value })}
              >
                {performanceYears.map((year) => (
                  <option key={year} value={year}>{year}</option>
                ))}
              </select>
            </label>
            <ArrowRight aria-hidden="true" />
            <label>
              <span className="sr-only">Dashboard comparison year</span>
              <select
                aria-label="Dashboard comparison year"
                value={filters.to}
                onChange={(event) => updateComparison({ to: event.target.value })}
              >
                {performanceYears.map((year) => (
                  <option key={year} value={year}>{year}</option>
                ))}
              </select>
            </label>
          </div>
          {filters.from === filters.to && <small>Choose two different years to see changes.</small>}
        </div>

        <div className="measure-count-card">
          <strong>{measuresInComparisonYear}</strong>
          <span>
            of {measures.length} {dataMode === "demo" ? "fictional" : "published"} measures in
            PY{filters.to}
          </span>
          {dataMode === "demo" && <DemoBadge />}
        </div>
      </section>

      <div className="home-ledger-card surface-card">
        <ChangeLedger
          filters={filters}
          measures={measures}
          onStatus={openStatus}
          dataMode={dataMode}
        />
      </div>

      <nav className="dashboard-next" aria-label="Continue exploring">
        <Link to="/measures" search={filters}>
          <Rows3 aria-hidden="true" />
          <span>
            <small>Measure Explorer</small>
            <strong>Browse the complete measure directory</strong>
          </span>
          <ArrowRight aria-hidden="true" />
        </Link>
        <Link to="/whats-new" search={filters}>
          <Newspaper aria-hidden="true" />
          <span>
            <small>What&apos;s new</small>
            <strong>Follow published updates and review status</strong>
          </span>
          <ArrowRight aria-hidden="true" />
        </Link>
      </nav>
    </div>
  );
}

function DemoDashboardPage({ filters }: { filters: DemoFilters }) {
  const measureQuery = useDemoMeasureList({
    ...filters,
    q: "",
    status: "all",
    year: "all",
    field: "all",
    review: "all",
  });

  if (!measureQuery.data) {
    return <LoadingState label="Loading fictional prototype measures…" />;
  }

  return (
    <DashboardContent
      filters={filters}
      measures={measureQuery.data.items}
      performanceYears={[2025, 2026]}
      dataMode="demo"
    />
  );
}

function ApiDashboardPage({ filters }: { filters: DemoFilters }) {
  const measureQuery = useApiMeasureList({
    ...filters,
    q: "",
    status: "all",
    year: "all",
    field: "all",
    review: "all",
  });
  const performanceYearsQuery = usePerformanceYears();

  if (measureQuery.isPending || performanceYearsQuery.isPending) {
    return <LoadingState label="Loading published measures…" />;
  }
  if (measureQuery.isError || performanceYearsQuery.isError) {
    const error = measureQuery.error ?? performanceYearsQuery.error;
    return (
      <ErrorState
        message={error?.message ?? "Published measure data could not be loaded."}
        onRetry={() => {
          void measureQuery.refetch();
          void performanceYearsQuery.refetch();
        }}
      />
    );
  }

  return (
    <DashboardContent
      filters={filters}
      measures={measureQuery.data.items.map(apiSummaryToMeasure)}
      performanceYears={performanceYearsQuery.data.years}
      dataMode="api"
    />
  );
}

export function DashboardPage() {
  const rawSearch = useSearch({ from: "/" });
  const filters = parseDemoFilters(rawSearch);

  return getDataMode() === "demo" ? (
    <DemoDashboardPage filters={filters} />
  ) : (
    <ApiDashboardPage filters={filters} />
  );
}
