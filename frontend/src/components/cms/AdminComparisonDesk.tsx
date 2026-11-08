import { useMemo, useState, type FormEvent } from "react";
import {
  Check,
  BookOpenCheck,
  CircleDashed,
  ExternalLink,
  FileSearch,
  GitCompareArrows,
  Globe2,
  RefreshCw,
} from "lucide-react";

import {
  type AdminComparison,
  useAdminComparisonPreparation,
  useAdminComparisonPublication,
  useAdminComparisonReview,
  useAdminComparisons,
} from "../../features/admin/api";
import { Button } from "../ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "../ui/dialog";
import { StatusMark } from "./shared";
import { AdminImpactReviewDialog } from "./AdminImpactReviewDialog";

const FROM_YEAR = 2025;
const TO_YEAR = 2026;

function humanize(value: string) {
  return value.replaceAll("_", " ");
}

function conciseEvidenceLocator(locator: string | null, officialUrl: string) {
  const value = locator ?? "";
  const isPdf = /^pdf\b/i.test(value) || /\.pdf(?:$|[?#])/i.test(officialUrl);
  const format = isPdf ? "PDF" : "HTML";
  const pageMatch = value.match(/pages?\s+(\d+)(?:\s*[-–]\s*(\d+))?/i);
  const tableMatch = value.match(/table\s+(\d+)/i);
  const pageLabel = pageMatch
    ? `${pageMatch[2] ? "pp." : "p."} ${pageMatch[1]}${pageMatch[2] ? `–${pageMatch[2]}` : ""}`
    : null;
  const tableLabel = tableMatch ? `Table ${tableMatch[1]}` : null;
  return [format, pageLabel, tableLabel].filter(Boolean).join(" · ");
}

function ComparisonReviewDialog({
  comparison,
  onClose,
}: {
  comparison: AdminComparison | null;
  onClose: () => void;
}) {
  const review = useAdminComparisonReview(FROM_YEAR, TO_YEAR);
  const [decision, setDecision] = useState<"approve" | "needs_revision">("approve");
  const [notes, setNotes] = useState("");

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!comparison) return;
    review.mutate(
      {
        comparisonId: comparison.comparison_id,
        decision,
        reviewerNotes: notes.trim() || null,
      },
      { onSuccess: onClose },
    );
  }

  return (
    <Dialog open={comparison !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="admin-comparison-review-dialog">
        <div>
          <p className="card-kicker">Private comparison review</p>
          <DialogTitle>
            {comparison?.measure_id} · PY{FROM_YEAR}–PY{TO_YEAR}
          </DialogTitle>
          <DialogDescription>
            Confirm the deterministic finding against its linked official evidence.
          </DialogDescription>
        </div>
        <form onSubmit={submit}>
          <fieldset className="admin-comparison-decision">
            <legend>Review decision</legend>
            <label>
              <input
                type="radio"
                name="comparison-decision"
                value="approve"
                checked={decision === "approve"}
                onChange={() => setDecision("approve")}
              />
              <span><Check aria-hidden="true" /> Approve</span>
            </label>
            <label>
              <input
                type="radio"
                name="comparison-decision"
                value="needs_revision"
                checked={decision === "needs_revision"}
                onChange={() => setDecision("needs_revision")}
              />
              <span><RefreshCw aria-hidden="true" /> Needs revision</span>
            </label>
          </fieldset>
          <label className="admin-textarea-field">
            <span>Reviewer notes{decision === "needs_revision" ? " (required)" : " (optional)"}</span>
            <textarea
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              required={decision === "needs_revision"}
              maxLength={4000}
              rows={4}
            />
          </label>
          {review.isError && <p className="admin-form-error" role="alert">{review.error.message}</p>}
          <div className="admin-review-actions">
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={review.isPending}>
              {review.isPending ? "Saving…" : "Save comparison review"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function ComparisonEvidence({ comparison }: { comparison: AdminComparison }) {
  const evidence = useMemo(
    () => comparison.fields.flatMap((field) => field.evidence),
    [comparison.fields],
  );
  const sources = [...new Map(evidence.map((item) => [item.evidence_id, item])).values()];
  const sourceGroups = [
    {
      side: "from_version",
      label: `PY${comparison.from_year}`,
      sources: sources.filter((source) => source.side === "from_version"),
    },
    {
      side: "to_version",
      label: `PY${comparison.to_year}`,
      sources: sources.filter((source) => source.side === "to_version"),
    },
    {
      side: "context",
      label: "Context",
      sources: sources.filter((source) => source.side === "context"),
    },
  ].filter((group) => group.sources.length > 0);

  return (
    <details className="admin-comparison-evidence">
      <summary>Inspect values and {sources.length} evidence links</summary>
      {comparison.fields.map((field) => (
        <div className="admin-comparison-values" key={field.field}>
          <span>{humanize(field.field)}</span>
          <article>
            <small>PY{comparison.from_year}</small>
            <p>{field.from_value ?? humanize(field.from_availability)}</p>
          </article>
          <article>
            <small>PY{comparison.to_year}</small>
            <p>{field.to_value ?? humanize(field.to_availability)}</p>
          </article>
        </div>
      ))}
      <div className="admin-comparison-sources">
        {sourceGroups.map((group) => (
          <section className="admin-comparison-source-group" key={group.side}>
            <p>
              {group.label} · {group.sources.length} official {group.sources.length === 1 ? "source" : "sources"}
            </p>
            {group.sources.map((source) => (
              <a
                key={source.evidence_id}
                href={source.official_url}
                target="_blank"
                rel="noreferrer"
              >
                <span>
                  <strong>{source.document_title}</strong>
                  <small title={source.locator ?? source.source_revision_id}>
                    {conciseEvidenceLocator(source.locator, source.official_url)}
                  </small>
                </span>
                <ExternalLink aria-hidden="true" />
              </a>
            ))}
          </section>
        ))}
      </div>
    </details>
  );
}

export function AdminComparisonDesk() {
  const comparisons = useAdminComparisons(FROM_YEAR, TO_YEAR, true);
  const preparation = useAdminComparisonPreparation(FROM_YEAR, TO_YEAR);
  const publication = useAdminComparisonPublication(FROM_YEAR, TO_YEAR);
  const [reviewing, setReviewing] = useState<AdminComparison | null>(null);
  const [impactReviewing, setImpactReviewing] = useState<AdminComparison | null>(null);

  const items = comparisons.data?.items ?? [];
  const reviewed = items.filter((item) => item.review_decision !== "pending").length;
  const published = items.filter((item) => item.publication_state === "published").length;

  return (
    <section className="admin-comparison-desk surface-card" aria-labelledby="comparison-desk-title">
      <header>
        <div>
          <p className="card-kicker">Comparison publication desk</p>
          <h2 id="comparison-desk-title">Evidence-backed changes</h2>
          <p>PY{FROM_YEAR} → PY{TO_YEAR} · Program roster</p>
        </div>
        <Button
          variant="outline"
          onClick={() => preparation.mutate()}
          disabled={preparation.isPending}
        >
          <GitCompareArrows aria-hidden="true" />
          {preparation.isPending ? "Preparing…" : "Prepare comparisons"}
        </Button>
      </header>

      <ol className="admin-comparison-rail" aria-label="Comparison publication progress">
        <li className={items.length > 0 ? "complete" : ""}>
          <span>{items.length > 0 ? <Check /> : <CircleDashed />}</span>
          <strong>{items.length}</strong>
          <small>Prepared</small>
        </li>
        <li className={reviewed > 0 ? "complete" : ""}>
          <span>{reviewed > 0 ? <Check /> : <CircleDashed />}</span>
          <strong>{reviewed}</strong>
          <small>Reviewed</small>
        </li>
        <li className={published > 0 ? "complete" : ""}>
          <span>{published > 0 ? <Check /> : <CircleDashed />}</span>
          <strong>{published}</strong>
          <small>Public</small>
        </li>
      </ol>

      {preparation.data && (
        <p className="admin-comparison-result" role="status">
          {preparation.data.prepared} prepared · {preparation.data.existing} already present
          {preparation.data.skipped_measure_ids.length > 0 &&
            ` · ${preparation.data.skipped_measure_ids.length} one-sided records safely skipped`}
        </p>
      )}
      {(preparation.isError || publication.isError) && (
        <p className="admin-form-error" role="alert">
          {preparation.error?.message ?? publication.error?.message}
        </p>
      )}

      {comparisons.isPending && <div className="admin-comparison-empty">Loading comparisons…</div>}
      {comparisons.isError && (
        <div className="admin-comparison-empty" role="alert">
          <p>{comparisons.error.message}</p>
          <Button variant="outline" onClick={() => void comparisons.refetch()}>Try again</Button>
        </div>
      )}
      {!comparisons.isPending && !comparisons.isError && items.length === 0 && (
        <div className="admin-comparison-empty">
          <FileSearch aria-hidden="true" />
          <p>No private comparisons have been prepared for this year pair.</p>
        </div>
      )}

      <div className="admin-comparison-list">
        {items.map((comparison) => (
          <article className="admin-comparison-card" key={comparison.comparison_id}>
            <header>
              <div>
                <span className="admin-measure-id">{comparison.measure_id}</span>
                <h3>{comparison.measure_name}</h3>
              </div>
              <StatusMark status={comparison.status} badge />
            </header>
            <div className="admin-comparison-state">
              <span className={`evidence-${comparison.evidence_status}`}>
                {humanize(comparison.evidence_status)} evidence
              </span>
              <span>{humanize(comparison.review_decision)}</span>
              <span>{humanize(comparison.publication_state)}</span>
            </div>
            <ComparisonEvidence comparison={comparison} />
            {comparison.publication_blocker && (
              <p className="admin-comparison-blocker">{comparison.publication_blocker}</p>
            )}
            <footer>
              <Button
                variant="ghost"
                onClick={() => setImpactReviewing(comparison)}
                aria-label={`Review AI impact ${comparison.measure_id}`}
              >
                <BookOpenCheck aria-hidden="true" />
                AI impact
              </Button>
              <Button
                variant="outline"
                onClick={() => setReviewing(comparison)}
                disabled={comparison.publication_state === "published"}
                aria-label={`Review comparison ${comparison.measure_id}`}
              >
                Review
              </Button>
              <Button
                onClick={() => publication.mutate(comparison.comparison_id)}
                disabled={
                  comparison.publication_eligibility !== "eligible" || publication.isPending
                }
                aria-label={`Publish comparison ${comparison.measure_id}`}
              >
                <Globe2 aria-hidden="true" />
                {comparison.publication_state === "published" ? "Published" : "Publish"}
              </Button>
            </footer>
          </article>
        ))}
      </div>
      <ComparisonReviewDialog comparison={reviewing} onClose={() => setReviewing(null)} />
      <AdminImpactReviewDialog
        comparison={impactReviewing}
        onClose={() => setImpactReviewing(null)}
      />
    </section>
  );
}
