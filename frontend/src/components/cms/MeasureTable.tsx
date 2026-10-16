import { Link } from "@tanstack/react-router";
import { AlertTriangle, ArrowRight, Search } from "lucide-react";

import type { DemoFilters, DemoMeasure } from "../../features/measures/demo/types";
import { comparisonStatus, defaultDemoFilters } from "../../features/measures/demo/filters";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { FilterSelect, SectionTitle, StatusMark } from "./shared";

export function MeasureTable({
  filters,
  measures,
  total,
  onFiltersChange,
  dataMode = "demo",
}: {
  filters: DemoFilters;
  measures: DemoMeasure[];
  total: number;
  onFiltersChange: (values: Partial<DemoFilters>) => void;
  dataMode?: "api" | "demo";
}) {
  const options = (values: string[], first = "All") => [
    { value: "all", label: first },
    ...values.map((value) => ({ value, label: value })),
  ];

  const clearFilters = () =>
    onFiltersChange({ ...defaultDemoFilters, from: filters.from, to: filters.to });

  return (
    <section className="measures-section route-section" aria-labelledby="measure-directory-title">
      <div className="section-heading-row">
        <div id="measure-directory-title">
          <SectionTitle demo={dataMode === "demo"}>Measure directory</SectionTitle>
        </div>
        <span className="quiet-label" aria-live="polite">
          Showing {measures.length} of {total} {dataMode === "demo" ? "fictional " : ""}measures
        </span>
      </div>

      <div className="table-filters">
        <div className="table-search">
          <Search size={15} />
          <Input
            aria-label="Search measures"
            placeholder="Search by ID, name, or description"
            type="search"
            value={filters.q}
            onChange={(event) => onFiltersChange({ q: event.target.value })}
          />
        </div>
        <FilterSelect
          label="Status"
          value={filters.status}
          options={[
            { value: "all", label: "All" },
            ...[
              "added",
              "removed",
              "modified",
              "unchanged",
              ...(dataMode === "api" ? ["unknown"] : []),
            ].map((value) => ({
              value,
              label: value.charAt(0).toUpperCase() + value.slice(1),
            })),
          ]}
          onChange={(status) => onFiltersChange({ status })}
        />
        <FilterSelect
          label="Year"
          value={filters.year}
          options={[
            { value: "all", label: "Both" },
            { value: "2025", label: "PY2025" },
            { value: "2026", label: "PY2026" },
          ]}
          onChange={(year) => onFiltersChange({ year })}
        />
        <FilterSelect
          label="Field"
          value={filters.field}
          options={options([
            "Definition",
            "Numerator",
            "Denominator",
            "Exclusions",
            "Eligibility",
            "Calculation logic",
            "Measure set",
            ...(dataMode === "demo" ? ["No change"] : []),
          ])}
          onChange={(field) => onFiltersChange({ field })}
        />
        <FilterSelect
          label="Review"
          value={filters.review}
          options={options(["Approved", "In review", "Needs re-verification"])}
          onChange={(review) => onFiltersChange({ review })}
        />
        <Button variant="link" className="clear-filters" onClick={clearFilters}>
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
            {measures.map((measure) => (
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
                    <span className="unavailable-label">
                      Unavailable in {dataMode === "demo" ? "fictional " : "approved "}source
                    </span>
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

      {measures.length === 0 && (
        <div className="empty-state">
          <h3>No {dataMode === "demo" ? "fictional " : ""}measures match these filters.</h3>
          <Button variant="link" onClick={clearFilters}>
            Clear filters
          </Button>
        </div>
      )}
    </section>
  );
}
