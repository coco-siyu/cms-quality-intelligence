import { Link } from "@tanstack/react-router";
import { List, Search } from "lucide-react";
import { useState } from "react";

import { Button } from "../ui/button";
import { comparisonStatus } from "../../features/measures/demo/filters";
import type {
  DemoFilters,
  DemoMeasure,
  DemoStatus,
} from "../../features/measures/demo/types";
import type { DataMode } from "../../features/measures/dataMode";
import { SectionTitle } from "./shared";
import { statusIcons, statusLabels } from "./statusPresentation";

export function ChangeLedger({
  filters,
  measures,
  onStatus,
  dataMode,
}: {
  filters: DemoFilters;
  measures: DemoMeasure[];
  onStatus: (status: string) => void;
  dataMode: DataMode;
}) {
  const [query, setQuery] = useState("");
  const displayStatus = (measure: DemoMeasure) =>
    dataMode === "api" ? measure.status : comparisonStatus(measure, filters);
  const all = measures.filter(
    (measure) => filters.from !== filters.to || measure.years.includes(Number(filters.from)),
  );
  const order: DemoStatus[] = [
    "added",
    "modified",
    "wording_only",
    "unchanged",
    "removed",
    "unknown",
  ];
  const columns = [...all].sort(
    (a, b) => order.indexOf(displayStatus(a)) - order.indexOf(displayStatus(b)),
  );
  const normalizedQuery = query.trim().toLowerCase();
  const matchingMeasures = normalizedQuery
    ? columns.filter((measure) =>
        [measure.id, measure.name, measure.field, statusLabels[displayStatus(measure)]]
          .join(" ")
          .toLowerCase()
          .includes(normalizedQuery),
      )
    : columns;

  return (
    <section className="ledger-section">
      <SectionTitle demo={dataMode === "demo"}>
        What changed from PY{filters.from} to PY{filters.to}
      </SectionTitle>
      <p className="section-subtext">
        {filters.from === filters.to
          ? `Same-year ${dataMode === "demo" ? "fictional " : ""}comparison · No year-over-year changes.`
          : dataMode === "demo"
            ? "MSSP / APP Plus · Fictional performance-year membership and specification changes"
            : "MSSP / APP Plus · Published performance-year comparison records"}
      </p>
      <div className="ledger-scroll">
        <div className="ledger-chart">
          <div className="year-axis">
            <span>PY{filters.from}</span>
            <span>PY{filters.to}</span>
          </div>
          <div className="ledger-columns">
            {columns.map((measure) => {
              const status = displayStatus(measure);
              return (
                <Button
                  key={measure.id}
                  asChild
                  variant="ghost"
                  className={`ledger-column status-${status} ${
                    filters.status !== "all" && filters.status !== status ? "dimmed" : ""
                  }`}
                >
                  <Link
                    to="/measures/$measureId"
                    params={{ measureId: measure.id }}
                    search={filters}
                    title={`${measure.id} · ${measure.name} · ${statusLabels[status]}`}
                    aria-label={`${measure.id} ${measure.name}, ${statusLabels[status]}`}
                  >
                    <span className={`ledger-node ${status === "added" ? "hollow" : ""}`} />
                    <span className="ledger-line" />
                    <span className={`ledger-node ${status === "removed" ? "hollow" : ""}`} />
                    <span className="ledger-id">{measure.id}</span>
                  </Link>
                </Button>
              );
            })}
            {columns.length === 0 && (
              <div className="ledger-empty-rail" role="status">
                {filters.from === filters.to
                  ? "Choose two different years."
                  : "No published comparisons for this year pair."}
              </div>
            )}
          </div>
        </div>
      </div>
      <div className="summary-metrics">
        {(["all", "added", "removed", "modified", "unchanged"] as const).map((status) => {
          const Icon = status === "all" ? List : statusIcons[status];
          const selected = filters.status === status;
          return (
            <Button
              key={status}
              variant="ghost"
              aria-pressed={selected}
              aria-label={`View ${status === "all" ? "all" : status} measures in Measure Explorer`}
              onClick={() => onStatus(status)}
              className={`summary-metric ${
                status === "all" ? "status-total" : `status-${status}`
              } ${selected ? "selected" : ""}`}
            >
              <span className="metric-number">
                {status === "all"
                  ? all.length
                  : all.filter((measure) => displayStatus(measure) === status).length}
              </span>
              <span className="metric-label">
                <Icon size={13} />
                {status === "all" ? "Total measures" : statusLabels[status]}
              </span>
            </Button>
          );
        })}
      </div>

      <section className="change-register" aria-labelledby="change-register-title">
        <header>
          <div>
            <p className="card-kicker">Published comparison register</p>
            <h3 id="change-register-title">Evidence-backed changes</h3>
          </div>
          <label className="change-register-search">
            <Search aria-hidden="true" />
            <span className="sr-only">Search published changes</span>
            <input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search ID, measure, field, or status"
            />
          </label>
        </header>

        {columns.length === 0 ? (
          <div className="change-register-empty">
            {filters.from === filters.to ? (
              <>
                <strong>Choose two different performance years.</strong>
                <p>The comparison register is available only for a year-over-year view.</p>
              </>
            ) : (
              <>
                <strong>No verified change records are public yet.</strong>
                <p>
                  Published measures remain available in Measure Explorer. A comparison appears
                  here only after both year versions and their evidence have been approved.
                </p>
              </>
            )}
          </div>
        ) : matchingMeasures.length === 0 ? (
          <div className="change-register-empty" role="status">
            <strong>No published changes match this search.</strong>
            <button type="button" onClick={() => setQuery("")}>Clear search</button>
          </div>
        ) : (
          <div className="change-register-list" role="list">
            {matchingMeasures.map((measure) => {
              const status = displayStatus(measure);
              const Icon = statusIcons[status];
              return (
                <div key={`${measure.id}-${status}`} role="listitem">
                  <Link
                    to="/measures/$measureId"
                    params={{ measureId: measure.id }}
                    search={filters}
                    className="change-register-row"
                  >
                    <span className="change-register-id">{measure.id}</span>
                    <span className="change-register-name">{measure.name}</span>
                    <span className={`change-register-status status-${status}`}>
                      <Icon aria-hidden="true" />
                      {statusLabels[status]}
                    </span>
                    <span className="change-register-field">{measure.field}</span>
                    <span className="change-register-open">
                      View <span aria-hidden="true">→</span>
                    </span>
                  </Link>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </section>
  );
}
