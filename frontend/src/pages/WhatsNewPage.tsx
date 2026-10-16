import { useSearch } from "@tanstack/react-router";

import { NewsFeed } from "../components/cms/NewsFeed";
import { DemoBadge, LoadingState } from "../components/cms/shared";
import { parseDemoFilters } from "../features/measures/demo/filters";
import { useDemoNews } from "../features/measures/demo/queries";

export function WhatsNewPage() {
  const rawSearch = useSearch({ from: "/whats-new" });
  const filters = parseDemoFilters(rawSearch);
  const newsQuery = useDemoNews();

  if (!newsQuery.data) {
    return <LoadingState label="Loading fictional prototype updates…" />;
  }

  return (
    <>
      <header className="route-page-header">
        <span className="route-kicker">Publication ledger</span>
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
    </>
  );
}
