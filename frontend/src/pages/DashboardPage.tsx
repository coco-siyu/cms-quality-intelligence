import { Link, useNavigate, useSearch } from "@tanstack/react-router";
import { ArrowRight, Newspaper, Rows3 } from "lucide-react";

import { ChangeLedger } from "../components/cms/ChangeLedger";
import { DemoBadge, LoadingState } from "../components/cms/shared";
import { parseDemoFilters } from "../features/measures/demo/filters";
import { useDemoMeasureList } from "../features/measures/demo/queries";

export function DashboardPage() {
  const rawSearch = useSearch({ from: "/" });
  const filters = parseDemoFilters(rawSearch);
  const navigate = useNavigate({ from: "/" });
  const ledgerQuery = useDemoMeasureList({
    ...filters,
    q: "",
    status: "all",
    year: "all",
    field: "all",
    review: "all",
  });

  if (!ledgerQuery.data) {
    return <LoadingState label="Loading fictional prototype measures…" />;
  }

  function openStatus(status: string) {
    void navigate({
      to: "/measures",
      search: { ...filters, status },
    });
  }

  return (
    <>
      <header className="dashboard-header">
        <div className="route-title-row">
          <h1>CMS Quality Intelligence</h1>
          <DemoBadge />
        </div>
        <p>Track, understand, and act on CMS quality measure changes.</p>
      </header>

      <ChangeLedger
        filters={filters}
        measures={ledgerQuery.data.items}
        onStatus={openStatus}
      />

      <nav className="dashboard-next" aria-label="Continue exploring">
        <Link to="/measures" search={filters}>
          <Rows3 size={18} />
          <span>
            <small>Measure Explorer</small>
            <strong>Browse the complete fictional measure set</strong>
          </span>
          <ArrowRight size={16} />
        </Link>
        <Link to="/whats-new" search={filters}>
          <Newspaper size={18} />
          <span>
            <small>What&apos;s new</small>
            <strong>Read the latest fictional updates</strong>
          </span>
          <ArrowRight size={16} />
        </Link>
      </nav>
    </>
  );
}
