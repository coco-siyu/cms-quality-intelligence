import { ExternalLink } from "lucide-react";

import type { EvidenceReference, MeasureVersion } from "../../features/measures/api/types";
import { formatApiDate } from "../../features/measures/api/adapters";
import { SectionTitle } from "./shared";

type TimelineEntry = {
  reference: EvidenceReference;
  years: number[];
};

function sourceTimelineEntries(versions: MeasureVersion[]): TimelineEntry[] {
  const entries = new Map<string, { reference: EvidenceReference; years: Set<number> }>();

  versions.forEach((version) => {
    version.fields.forEach((field) => {
      field.evidence.forEach((reference) => {
        const entry = entries.get(reference.source_revision_id) ?? {
          reference,
          years: new Set<number>(),
        };
        entry.years.add(version.performance_year);
        entries.set(reference.source_revision_id, entry);
      });
    });
  });

  return [...entries.values()]
    .map((entry) => ({
      reference: entry.reference,
      years: [...entry.years].sort((left, right) => left - right),
    }))
    .sort((left, right) => {
      const leftDate = left.reference.publication_date;
      const rightDate = right.reference.publication_date;
      if (leftDate && rightDate && leftDate !== rightDate) return rightDate.localeCompare(leftDate);
      if (leftDate && !rightDate) return -1;
      if (!leftDate && rightDate) return 1;
      return left.reference.source_revision_id.localeCompare(right.reference.source_revision_id);
    });
}

export function SourceTimeline({ versions }: { versions: MeasureVersion[] }) {
  const entries = sourceTimelineEntries(versions);

  return (
    <section className="source-timeline-section">
      <SectionTitle demo={false}>CMS source timeline</SectionTitle>
      <p className="section-subtext">
        Newest documented CMS publication first. Publication, applicability, and effective dates
        remain separate.
      </p>
      {entries.length === 0 ? (
        <p className="unavailable-text">No public source revision is available for this measure.</p>
      ) : (
        <ol className="source-publication-timeline" aria-label="CMS source publication timeline">
          {entries.map(({ reference, years }, index) => (
            <li key={reference.source_revision_id}>
              <div className="source-publication-date">
                <span>CMS publication</span>
                {reference.publication_date ? (
                  <time dateTime={reference.publication_date}>
                    {formatApiDate(reference.publication_date)}
                  </time>
                ) : (
                  <strong>Not documented</strong>
                )}
              </div>
              <article>
                <header>
                  <span>{String(index + 1).padStart(2, "0")}</span>
                  <h3>{reference.document_title}</h3>
                </header>
                <dl>
                  <div>
                    <dt>Source revision</dt>
                    <dd>{reference.source_revision_id}</dd>
                  </div>
                  <div>
                    <dt>Applies to</dt>
                    <dd>{years.map((year) => `PY${year}`).join(", ")}</dd>
                  </div>
                  <div>
                    <dt>Effective date</dt>
                    <dd>
                      {reference.effective_date
                        ? formatApiDate(reference.effective_date)
                        : "Not documented"}
                    </dd>
                  </div>
                </dl>
                <a href={reference.official_url} target="_blank" rel="noreferrer">
                  Open official source <ExternalLink aria-hidden="true" />
                </a>
              </article>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
