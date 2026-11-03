import { Link, useNavigate, useSearch } from "@tanstack/react-router";
import { ArrowRight, Newspaper, Rows3 } from "lucide-react";

import { ChangeLedger } from "../components/cms/ChangeLedger";
import { HeroCollage } from "../components/cms/HeroCollage";
import { DemoBadge, ErrorState, LoadingState } from "../components/cms/shared";
import { apiChangeToMeasure, apiSummaryToMeasure } from "../features/measures/api/adapters";
import {
  useApiChanges,
  useApiMeasureList,
  usePerformanceYears,
} from "../features/measures/api/queries";
import { getDataMode, type DataMode } from "../features/measures/dataMode";
import { parseDemoFilters } from "../features/measures/demo/filters";
import { useDemoMeasureList } from "../features/measures/demo/queries";
import type { DemoFilters, DemoMeasure } from "../features/measures/demo/types";

function DashboardContent({
  filters,
  measures,
  comparisonMeasures,
  performanceYears,
  dataMode,
}: {
  filters: DemoFilters;
  measures: DemoMeasure[];
  comparisonMeasures: DemoMeasure[];
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
          measures={comparisonMeasures}
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
      comparisonMeasures={measureQuery.data.items}
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
  const changeQuery = useApiChanges(Number(filters.from), Number(filters.to));
  const sameYear = filters.from === filters.to;

  if (measureQuery.isPending || performanceYearsQuery.isPending || (!sameYear && changeQuery.isPending)) {
    return <LoadingState label="Loading published measures…" />;
  }
  if (measureQuery.isError || performanceYearsQuery.isError || changeQuery.isError) {
    const error = measureQuery.error ?? performanceYearsQuery.error ?? changeQuery.error;
    return (
      <ErrorState
        message={error?.message ?? "Published measure data could not be loaded."}
        onRetry={() => {
          void measureQuery.refetch();
          void performanceYearsQuery.refetch();
          if (!sameYear) void changeQuery.refetch();
        }}
      />
    );
  }

  const summaries = new Map(measureQuery.data.items.map((item) => [item.measure_id, item]));
  const comparisonMeasures = sameYear
    ? []
    : (changeQuery.data?.items ?? []).map((change) =>
        apiChangeToMeasure(change, summaries.get(change.measure_id)),
      );

  return (
    <DashboardContent
      filters={filters}
      measures={measureQuery.data.items.map(apiSummaryToMeasure)}
      comparisonMeasures={comparisonMeasures}
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
