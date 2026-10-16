import { Link } from "@tanstack/react-router";
import { List } from "lucide-react";

import { Button } from "../ui/button";
import { comparisonStatus } from "../../features/measures/demo/filters";
import type {
  DemoFilters,
  DemoMeasure,
  DemoStatus,
} from "../../features/measures/demo/types";
import { SectionTitle } from "./shared";
import { statusIcons, statusLabels } from "./statusPresentation";

export function ChangeLedger({
  filters,
  measures,
  onStatus,
}: {
  filters: DemoFilters;
  measures: DemoMeasure[];
  onStatus: (status: string) => void;
}) {
  const all = measures.filter(
    (measure) => filters.from !== filters.to || measure.years.includes(Number(filters.from)),
  );
  const order: DemoStatus[] = ["added", "modified", "unchanged", "removed"];
  const columns = [...all].sort(
    (a, b) => order.indexOf(comparisonStatus(a, filters)) - order.indexOf(comparisonStatus(b, filters)),
  );

  return (
    <section className="ledger-section">
      <SectionTitle>
        What changed from PY{filters.from} to PY{filters.to}
      </SectionTitle>
      <p className="section-subtext">
        {filters.from === filters.to
          ? "Same-year fictional comparison · No year-over-year changes."
          : "MSSP / APP Plus · Fictional performance-year membership and specification changes"}
      </p>
      <div className="ledger-scroll">
        <div className="ledger-chart">
          <div className="year-axis">
            <span>PY{filters.from}</span>
            <span>PY{filters.to}</span>
          </div>
          <div className="ledger-columns">
            {columns.map((measure) => {
              const status = comparisonStatus(measure, filters);
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
              onClick={() => onStatus(selected && status !== "all" ? "all" : status)}
              className={`summary-metric ${
                status === "all" ? "status-total" : `status-${status}`
              } ${selected ? "selected" : ""}`}
            >
              <span className="metric-number">
                {status === "all"
                  ? all.length
                  : all.filter((measure) => comparisonStatus(measure, filters) === status).length}
              </span>
              <span className="metric-label">
                <Icon size={13} />
                {status === "all" ? "Total measures" : statusLabels[status]}
              </span>
            </Button>
          );
        })}
      </div>
    </section>
  );
}
