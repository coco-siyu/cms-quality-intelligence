import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { ArrowRight, CheckCircle2, CircleDashed, RefreshCw, Rows3 } from "lucide-react";

import {
  type AdminReviewDashboardStatus,
  useAdminReviewDashboard,
} from "../../features/admin/api";
import { Button } from "../ui/button";

type DashboardFilter = AdminReviewDashboardStatus | "all";

const filters: { value: DashboardFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "pending", label: "Pending" },
  { value: "in_review", label: "In review" },
  { value: "completed", label: "Completed" },
  { value: "needs_re_review", label: "Needs re-review" },
];

const statusLabels: Record<AdminReviewDashboardStatus, string> = {
  pending: "Pending",
  in_review: "In review",
  completed: "Completed",
  needs_re_review: "Needs re-review",
};

function statusIcon(status: AdminReviewDashboardStatus) {
  if (status === "completed") return <CheckCircle2 aria-hidden="true" />;
  if (status === "needs_re_review") return <RefreshCw aria-hidden="true" />;
  return <CircleDashed aria-hidden="true" />;
}

export function AdminReviewDashboard() {
  const [filter, setFilter] = useState<DashboardFilter>("all");
  const dashboard = useAdminReviewDashboard(filter === "all" ? undefined : filter, true);
  const summary = dashboard.data?.summary;
  const items = dashboard.data?.items ?? [];

  function countFor(value: DashboardFilter) {
    if (!summary) return 0;
    return value === "all" ? summary.total : summary[value];
  }

  return (
    <section className="admin-review-dashboard surface-card" aria-labelledby="review-dashboard-title">
      <header>
        <div>
          <p className="card-kicker">Review operations</p>
          <h2 id="review-dashboard-title">Measure review dashboard</h2>
          <p>Accepted tasks and checklist progress across private measure reviews.</p>
        </div>
        <span className="admin-review-dashboard-total">
          <Rows3 aria-hidden="true" />
          <strong>{summary?.total ?? 0}</strong> reviews
        </span>
      </header>

      <div className="admin-review-dashboard-filters" aria-label="Filter measure reviews">
        {filters.map((item) => (
          <button
            type="button"
            key={item.value}
            className={filter === item.value ? "is-active" : ""}
            aria-pressed={filter === item.value}
            onClick={() => setFilter(item.value)}
          >
            <span>{item.label}</span>
            <strong>{countFor(item.value)}</strong>
          </button>
        ))}
      </div>

      {dashboard.isPending && (
        <div className="admin-review-dashboard-empty">Loading review progress…</div>
      )}
      {dashboard.isError && (
        <div className="admin-review-dashboard-empty" role="alert">
          <p>{dashboard.error.message}</p>
          <Button variant="outline" onClick={() => void dashboard.refetch()}>Try again</Button>
        </div>
      )}
      {!dashboard.isPending && !dashboard.isError && items.length === 0 && (
        <div className="admin-review-dashboard-empty">
          No {filter === "all" ? "measure reviews" : statusLabels[filter].toLowerCase()} match this view.
        </div>
      )}

      <div className="admin-review-dashboard-list">
        {items.map((item) => {
          const percent = item.progress.total === 0
            ? 0
            : Math.round((item.progress.resolved / item.progress.total) * 100);
          return (
            <article
              className={`admin-review-dashboard-row status-${item.dashboard_status}`}
              key={item.comparison_id}
            >
              <span className="admin-review-dashboard-marker" aria-hidden="true" />
              <div className="admin-review-dashboard-measure">
                <span className="admin-measure-id">{item.measure_id}</span>
                <h3>{item.measure_name}</h3>
                <small>PY{item.from_year} → PY{item.to_year}</small>
              </div>
              <div className="admin-review-dashboard-state">
                <span className={`admin-review-dashboard-badge status-${item.dashboard_status}`}>
                  {statusIcon(item.dashboard_status)}
                  {statusLabels[item.dashboard_status]}
                </span>
                <small>{item.remaining_tasks} remaining</small>
              </div>
              <div className="admin-review-dashboard-progress">
                <span>
                  <strong>{item.progress.resolved}</strong> of {item.progress.total} resolved
                </span>
                <div
                  role="progressbar"
                  aria-label={`${item.measure_id} checklist progress`}
                  aria-valuemin={0}
                  aria-valuemax={item.progress.total}
                  aria-valuenow={item.progress.resolved}
                >
                  <span style={{ width: `${percent}%` }} />
                </div>
              </div>
              <Link
                to="/admin/measures/$measureId"
                params={{ measureId: item.measure_id }}
                aria-label={`Open review for ${item.measure_id}`}
              >
                Open measure <ArrowRight aria-hidden="true" />
              </Link>
            </article>
          );
        })}
      </div>
    </section>
  );
}
