import { Link, useSearch } from "@tanstack/react-router";
import { ArrowRight, ShieldCheck } from "lucide-react";

import { NewsFeed } from "../components/cms/NewsFeed";
import { DemoBadge, LoadingState } from "../components/cms/shared";
import { getDataMode } from "../features/measures/dataMode";
import { parseDemoFilters } from "../features/measures/demo/filters";
import { useDemoNews } from "../features/measures/demo/queries";

function PublicWhatsNewPage() {
  const rawSearch = useSearch({ from: "/whats-new" });
  const filters = parseDemoFilters(rawSearch);

  return (
    <div className="visual-page news-page">
      <header className="news-page-header">
        <p className="page-eyebrow">Publication ledger</p>
        <h1>What&apos;s new</h1>
        <p>
          Follow approved measure-set and specification updates for the selected performance-year
          comparison.
        </p>
      </header>
      <article className="news-awaiting-card">
        <ShieldCheck aria-hidden="true" />
        <div>
          <p className="card-kicker">Published data only</p>
          <h2>The public update feed is being prepared.</h2>
          <p>
            The current API does not yet publish a chronological update feed. No fictional CMS
            events have been substituted. Approved measures remain available in the directory.
          </p>
          <Link to="/measures" search={filters}>
            Open Measure Explorer <ArrowRight aria-hidden="true" />
          </Link>
        </div>
      </article>
    </div>
  );
}

function DemoWhatsNewPage() {
  const rawSearch = useSearch({ from: "/whats-new" });
  const filters = parseDemoFilters(rawSearch);
  const newsQuery = useDemoNews();

  if (!newsQuery.data) {
    return <LoadingState label="Loading fictional prototype updates…" />;
  }

  return (
    <div className="visual-page news-page">
      <header className="news-page-header">
        <p className="page-eyebrow">Publication ledger</p>
        <div className="route-title-row">
          <h1>What&apos;s new</h1>
          <DemoBadge />
        </div>
        <p>
          A focused feed of fictional measure-set and specification updates for the selected
          performance-year comparison.
        </p>
      </header>
      <NewsFeed items={newsQuery.data} filters={filters} />
    </div>
  );
}

export function WhatsNewPage() {
  return getDataMode() === "demo" ? <DemoWhatsNewPage /> : <PublicWhatsNewPage />;
}
