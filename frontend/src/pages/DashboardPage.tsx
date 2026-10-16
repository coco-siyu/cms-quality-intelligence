import { useSearch, useNavigate, Link } from "@tanstack/react-router";
import { AlertTriangle, ArrowRight, Search } from "lucide-react";

import { ChangeLedger } from "../components/cms/ChangeLedger";
import { FilterSelect, LoadingState, SectionTitle, StatusMark } from "../components/cms/shared";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { comparisonStatus, defaultDemoFilters, parseDemoFilters } from "../features/measures/demo/filters";
import { useDemoMeasureList, useDemoNews } from "../features/measures/demo/queries";

export function DashboardPage() {
  const rawSearch = useSearch({ strict: false });
  const filters = parseDemoFilters(rawSearch);
  const navigate = useNavigate({ from: "/" });
  const measureQuery = useDemoMeasureList(filters);
  const ledgerQuery = useDemoMeasureList({
    ...filters,
    q: "",
    status: "all",
    year: "all",
    field: "all",
    review: "all",
  });
  const newsQuery = useDemoNews();

  function update(values: Partial<typeof filters>) {
    void navigate({ search: { ...filters, ...values }, replace: true });
  }

  if (!measureQuery.data || !ledgerQuery.data || !newsQuery.data) {
    return <LoadingState label="Loading fictional prototype measures…" />;
  }

  const rows = measureQuery.data.items;
  const options = (values: string[], first = "All") => [
    { value: "all", label: first },
    ...values.map((value) => ({ value, label: value })),
  ];

  return (
    <>
      <header className="dashboard-header">
        <h1>CMS Quality Intelligence</h1>
        <p>Track, understand, and act on CMS quality measure changes.</p>
      </header>

      <ChangeLedger
        filters={filters}
        measures={ledgerQuery.data.items}
        onStatus={(status) => update({ status })}
      />

      <section id="whats-new" className="news-section">
        <div className="section-heading-row">
          <SectionTitle>What&apos;s new</SectionTitle>
          <span className="quiet-label">Latest fictional updates</span>
        </div>
        <div className="news-grid">
          {newsQuery.data.map((item) => (
            <article key={item.id} className="news-item">
              <div className="news-status">
                <StatusMark status={item.status} />
                {item.id === "PV-103" && (
                  <span className="warning-text">Needs re-verification</span>
                )}
              </div>
              <h3>{item.title}</h3>
              <p>{item.body}</p>
              <div className="news-dates">
                <div>
                  <span>Fictional publication</span>
                  <strong>{item.date}</strong>
                </div>
                <div>
                  <span>Applies to</span>
                  <strong>{item.applies}</strong>
                </div>
              </div>
              <Link
                to="/measures/$measureId"
                params={{ measureId: item.id }}
                search={filters}
                className="measure-link"
              >
                <span className="font-mono">{item.id}</span> View measure <ArrowRight size={13} />
              </Link>
            </article>
          ))}
        </div>
      </section>

      <section id="measures" className="measures-section">
        <div className="section-heading-row">
          <SectionTitle>Measures</SectionTitle>
          <span className="quiet-label" aria-live="polite">
            Showing {rows.length} of {measureQuery.data.total} fictional measures
          </span>
        </div>
        <div className="table-filters">
          <div className="table-search">
            <Search size={15} />
            <Input
              aria-label="Search measures"
              placeholder="Search by ID or name"
              type="search"
              value={filters.q}
              onChange={(event) => update({ q: event.target.value })}
            />
          </div>
          <FilterSelect
            label="Status"
            value={filters.status}
            options={[
              { value: "all", label: "All" },
              ...["added", "removed", "modified", "unchanged"].map((value) => ({
                value,
                label: value.charAt(0).toUpperCase() + value.slice(1),
              })),
            ]}
            onChange={(status) => update({ status })}
          />
          <FilterSelect
            label="Year"
            value={filters.year}
            options={[
              { value: "all", label: "Both" },
              { value: "2025", label: "PY2025" },
              { value: "2026", label: "PY2026" },
            ]}
            onChange={(year) => update({ year })}
          />
          <FilterSelect
            label="Field"
            value={filters.field}
            options={options([
              "Numerator",
              "Denominator",
              "Exclusions",
              "Eligibility",
              "Calculation logic",
              "Measure set",
              "No change",
            ])}
            onChange={(field) => update({ field })}
          />
          <FilterSelect
            label="Review"
            value={filters.review}
            options={options(["Approved", "In review", "Needs re-verification"])}
            onChange={(review) => update({ review })}
          />
          <Button
            variant="link"
            className="clear-filters"
            onClick={() => update({ ...defaultDemoFilters, from: filters.from, to: filters.to })}
          >
            Clear filters
          </Button>
        </div>

        <div className="table-scroll">
          <table className="measures-table">
            <thead>
              <tr>
                {["Measure ID", "Measure name", "Change", "Affected area", "Last verified", "Details"].map(
                  (heading) => (
                    <th key={heading} scope="col">
                      {heading}
                    </th>
                  ),
                )}
              </tr>
            </thead>
            <tbody>
              {rows.map((measure) => (
                <tr key={measure.id}>
                  <td>
                    <Link
                      to="/measures/$measureId"
                      params={{ measureId: measure.id }}
                      search={filters}
                      className="id-link"
                    >
                      {measure.id}
                    </Link>
                  </td>
                  <td className="measure-name">
                    <Link
                      to="/measures/$measureId"
                      params={{ measureId: measure.id }}
                      search={filters}
                    >
                      {measure.name}
                    </Link>
                  </td>
                  <td>
                    <StatusMark status={comparisonStatus(measure, filters)} />
                  </td>
                  <td>
                    {measure.field}
                    {measure.unavailable && (
                      <span className="unavailable-label">Unavailable in fictional source</span>
                    )}
                  </td>
                  <td>
                    {measure.verified}
                    {measure.review === "Needs re-verification" && (
                      <span className="verification-note">
                        <AlertTriangle size={12} /> Needs re-verification
                      </span>
                    )}
                    {measure.review === "In review" && <span className="review-note">In review</span>}
                  </td>
                  <td>
                    <Link
                      to="/measures/$measureId"
                      params={{ measureId: measure.id }}
                      search={filters}
                      className="measure-link"
                    >
                      View <ArrowRight size={14} />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {rows.length === 0 && (
          <div className="empty-state">
            <h3>No fictional measures match these filters.</h3>
            <Button
              variant="link"
              onClick={() => update({ ...defaultDemoFilters, from: filters.from, to: filters.to })}
            >
              Clear filters
            </Button>
          </div>
        )}
      </section>
    </>
  );
}
