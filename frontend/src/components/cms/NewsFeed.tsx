import { Link } from "@tanstack/react-router";
import { AlertTriangle, ArrowRight } from "lucide-react";

import type { DemoFilters, DemoNewsItem } from "../../features/measures/demo/types";
import { StatusMark } from "./shared";

export function NewsFeed({ items, filters }: { items: DemoNewsItem[]; filters: DemoFilters }) {
  return (
    <section className="editorial-feed" aria-label="Fictional CMS measure updates">
      {items.map((item) => (
        <article key={item.id} className="editorial-update">
          <div className="update-rail">
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
