import { useNavigate, useSearch } from "@tanstack/react-router";

import { MeasureTable } from "../components/cms/MeasureTable";
import { LoadingState } from "../components/cms/shared";
import { parseDemoFilters } from "../features/measures/demo/filters";
import { useDemoMeasureList } from "../features/measures/demo/queries";

export function MeasureExplorerPage() {
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
