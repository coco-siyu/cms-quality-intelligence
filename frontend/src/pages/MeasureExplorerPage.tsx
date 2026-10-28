import { useNavigate, useSearch } from "@tanstack/react-router";
import { Download } from "lucide-react";

import { MeasureTable } from "../components/cms/MeasureTable";
import { ErrorState, LoadingState } from "../components/cms/shared";
import { Button } from "../components/ui/button";
import { apiSummaryToMeasure } from "../features/measures/api/adapters";
import { useApiMeasureList, usePerformanceYears } from "../features/measures/api/queries";
import { getDataMode, type DataMode } from "../features/measures/dataMode";
import { parseDemoFilters } from "../features/measures/demo/filters";
import { useDemoMeasureList } from "../features/measures/demo/queries";
import type { DemoFilters, DemoMeasure } from "../features/measures/demo/types";

function csvCell(value: string | number) {
  return `"${String(value).replaceAll('"', '""')}"`;
}

function exportMeasures(measures: DemoMeasure[], dataMode: DataMode) {
  const header = ["measure_id", "name", "change_status", "affected_area", "years", "review"];
  const rows = measures.map((measure) => [
    measure.id,
    measure.name,
    measure.status,
    measure.field,
    measure.years.join("|"),
    measure.review,
  ]);
  const blob = new Blob(
    [[header, ...rows].map((row) => row.map(csvCell).join(",")).join("\n")],
    { type: "text/csv;charset=utf-8" },
  );
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download =
    dataMode === "demo" ? "fictional-measure-prototype.csv" : "published-measures.csv";
  anchor.click();
  URL.revokeObjectURL(url);
}

function ExplorerContent({
  dataMode,
  filters,
  measures,
  performanceYears,
  total,
}: {
  dataMode: DataMode;
  filters: DemoFilters;
  measures: DemoMeasure[];
  performanceYears: number[];
  total: number;
}) {
  const navigate = useNavigate({ from: "/measures" });

  return (
    <div className="visual-page explorer-page">
      <header className="explorer-header">
        <div>
          <p className="page-eyebrow">Public measure directory</p>
          <h1>Measure Explorer</h1>
          <p>
            Search, filter, and compare MSSP / APP Plus measures across the selected performance
            years.
          </p>
        </div>
        <Button
          type="button"
          onClick={() => exportMeasures(measures, dataMode)}
          disabled={measures.length === 0}
          className="export-button"
        >
          <Download aria-hidden="true" /> Export CSV
        </Button>
      </header>

      <MeasureTable
        dataMode={dataMode}
        filters={filters}
        measures={measures}
        performanceYears={performanceYears}
        total={total}
        onFiltersChange={(values) =>
          void navigate({ search: { ...filters, ...values }, replace: true })
        }
      />
    </div>
  );
}

function DemoMeasureExplorerPage() {
  const rawSearch = useSearch({ from: "/measures" });
  const filters = parseDemoFilters(rawSearch);
  const measureQuery = useDemoMeasureList(filters);

  if (!measureQuery.data) {
    return <LoadingState label="Loading fictional prototype measures…" />;
  }

  return (
    <ExplorerContent
      dataMode="demo"
      filters={filters}
      measures={measureQuery.data.items}
      performanceYears={[2025, 2026]}
      total={measureQuery.data.total}
    />
  );
}

function ApiMeasureExplorerPage() {
  const rawSearch = useSearch({ from: "/measures" });
  const filters = parseDemoFilters(rawSearch);
  const measureQuery = useApiMeasureList(filters);
  const performanceYearsQuery = usePerformanceYears();

  if (measureQuery.isPending || performanceYearsQuery.isPending) {
    return <LoadingState label="Loading approved public measures…" />;
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
    <ExplorerContent
      dataMode="api"
      filters={filters}
      measures={measureQuery.data.items.map(apiSummaryToMeasure)}
      performanceYears={performanceYearsQuery.data.years}
      total={measureQuery.data.pagination.total_items}
    />
  );
}

export function MeasureExplorerPage() {
  return getDataMode() === "demo" ? <DemoMeasureExplorerPage /> : <ApiMeasureExplorerPage />;
}
