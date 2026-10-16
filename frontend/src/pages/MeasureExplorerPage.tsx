import { useNavigate, useSearch } from "@tanstack/react-router";

import { MeasureTable } from "../components/cms/MeasureTable";
import { ErrorState, LoadingState } from "../components/cms/shared";
import { apiSummaryToMeasure } from "../features/measures/api/adapters";
import { useApiMeasureList } from "../features/measures/api/queries";
import { getDataMode } from "../features/measures/dataMode";
import { parseDemoFilters } from "../features/measures/demo/filters";
import { useDemoMeasureList } from "../features/measures/demo/queries";

function DemoMeasureExplorerPage() {
  const rawSearch = useSearch({ from: "/measures" });
  const filters = parseDemoFilters(rawSearch);
  const navigate = useNavigate({ from: "/measures" });
  const measureQuery = useDemoMeasureList(filters);

  if (!measureQuery.data) {
    return <LoadingState label="Loading fictional prototype measures…" />;
  }

  return (
    <>
      <header className="route-page-header">
        <span className="route-kicker">Public prototype directory</span>
        <h1>Measure Explorer</h1>
        <p>
          Search the fictional measure set, narrow the comparison, and open a measure for its
          field-level evidence.
        </p>
      </header>

      <MeasureTable
        filters={filters}
        measures={measureQuery.data.items}
        total={measureQuery.data.total}
        onFiltersChange={(values) =>
          void navigate({ search: { ...filters, ...values }, replace: true })
        }
      />
    </>
  );
}

function ApiMeasureExplorerPage() {
  const rawSearch = useSearch({ from: "/measures" });
  const filters = parseDemoFilters(rawSearch);
  const navigate = useNavigate({ from: "/measures" });
  const measureQuery = useApiMeasureList(filters);

  if (measureQuery.isPending) {
    return <LoadingState label="Loading approved public measures…" />;
  }
  if (measureQuery.isError) {
    return (
      <ErrorState
        message={measureQuery.error.message}
        onRetry={() => void measureQuery.refetch()}
      />
    );
  }

  return (
    <>
      <header className="route-page-header">
        <span className="route-kicker">Public measure directory</span>
        <h1>Measure Explorer</h1>
        <p>
          Search published measure records, inspect explicit availability states, and follow each
          field to its approved source evidence.
        </p>
      </header>

      <MeasureTable
        dataMode="api"
        filters={filters}
        measures={measureQuery.data.items.map(apiSummaryToMeasure)}
        total={measureQuery.data.pagination.total_items}
        onFiltersChange={(values) =>
          void navigate({ search: { ...filters, ...values }, replace: true })
        }
      />
    </>
  );
}

export function MeasureExplorerPage() {
  return getDataMode() === "demo" ? <DemoMeasureExplorerPage /> : <ApiMeasureExplorerPage />;
}
