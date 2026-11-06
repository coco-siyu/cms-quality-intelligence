import { Link } from "@tanstack/react-router";
import { AlertTriangle, ArrowRight } from "lucide-react";

import type { DemoFilters, DemoNewsItem } from "../../features/measures/demo/types";
import type { PublicChangeRecord } from "../../features/measures/api/types";
import { StatusMark } from "./shared";

const dateFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  timeZone: "UTC",
});

function formatDate(value: string) {
  const normalized = value.length === 10
    ? `${value}T00:00:00Z`
    : /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?$/.test(value)
      ? `${value}Z`
      : value;
  return dateFormatter.format(new Date(normalized));
}

function humanizeField(value: string) {
  return value.replaceAll("_", " ");
}

function updateTitle(item: PublicChangeRecord) {
  switch (item.status) {
    case "added":
      return `${item.measure_name} added for PY${item.to_year}`;
    case "removed":
      return `${item.measure_name} not carried into PY${item.to_year}`;
    case "wording_only":
      return `Wording update published for ${item.measure_name}`;
    case "unchanged":
      return `${item.measure_name} confirmed across both years`;
    case "modified":
      return `Approved changes published for ${item.measure_name}`;
    default:
      return `Comparison published for ${item.measure_name}`;
  }
}

function updateSummary(item: PublicChangeRecord) {
  const fields = item.fields.map((field) => humanizeField(field.field));
  const fieldSummary = fields.length
    ? `Reviewed fields: ${fields.join(", ")}.`
    : "No field-level change was published.";
  return `The approved PY${item.from_year}–PY${item.to_year} comparison is classified as ${item.status.replaceAll("_", " ")}. ${fieldSummary}`;
}

function cmsPublicationDates(item: PublicChangeRecord) {
  return [...new Set(
    item.fields.flatMap((field) =>
      field.evidence.flatMap((evidence) => evidence.publication_date ?? []),
    ),
  )].sort();
}

export function NewsFeed({ items, filters }: { items: DemoNewsItem[]; filters: DemoFilters }) {
  return (
    <section className="editorial-feed" aria-label="Fictional CMS measure updates">
      {items.map((item, index) => (
        <article
          key={item.id}
          className={`editorial-update ${index === 0 ? "featured-update" : ""}`}
        >
          <div className="update-rail">
            {index === 0 && <span className="featured-label">Featured</span>}
            <StatusMark status={item.status} />
            {item.id === "PV-103" && (
              <span className="warning-text">
                <AlertTriangle size={12} /> Needs re-verification
              </span>
            )}
            <dl>
              <div>
                <dt>Fictional publication</dt>
                <dd>{item.date}</dd>
              </div>
              <div>
                <dt>Applies to</dt>
                <dd>{item.applies}</dd>
              </div>
            </dl>
          </div>
          <div className="update-story">
            <span className="update-measure-id">{item.id}</span>
            <h2>{item.title}</h2>
            <p>{item.body}</p>
            <Link
              to="/measures/$measureId"
              params={{ measureId: item.id }}
              search={filters}
              className="measure-link"
            >
              View measure <ArrowRight size={13} />
            </Link>
          </div>
        </article>
      ))}
    </section>
  );
}

export function PublishedNewsFeed({
  items,
  filters,
}: {
  items: PublicChangeRecord[];
  filters: DemoFilters;
}) {
  return (
    <section className="editorial-feed" aria-label="Published CMS measure updates">
      {items.map((item, index) => {
        const sourceDates = cmsPublicationDates(item);
        return (
          <article
            key={`${item.measure_id}-${item.from_year}-${item.to_year}-${item.collection_type}`}
            className={`editorial-update ${index === 0 ? "featured-update" : ""}`}
          >
            <div className="update-rail">
              {index === 0 && <span className="featured-label">Latest published update</span>}
              <StatusMark status={item.status} />
              <dl className="publication-clocks">
                <div>
                  <dt>CMS source dates</dt>
                  <dd>
                    {sourceDates.length
                      ? sourceDates.map(formatDate).join(" · ")
                      : "Not documented"}
                  </dd>
                </div>
                <div>
                  <dt>Internal approval</dt>
                  <dd>{formatDate(item.approved_at)}</dd>
                </div>
                <div>
                  <dt>Public update</dt>
                  <dd>{formatDate(item.published_at)}</dd>
                </div>
                <div>
                  <dt>Applies to</dt>
                  <dd>PY{item.from_year} → PY{item.to_year}</dd>
                </div>
              </dl>
            </div>
            <div className="update-story">
              <span className="update-measure-id">{item.measure_id}</span>
              <h2>{updateTitle(item)}</h2>
              <p>{updateSummary(item)}</p>
              <Link
                to="/measures/$measureId"
                params={{ measureId: item.measure_id }}
                search={filters}
                className="measure-link"
              >
                View approved comparison <ArrowRight size={13} />
              </Link>
            </div>
          </article>
        );
      })}
    </section>
  );
}
