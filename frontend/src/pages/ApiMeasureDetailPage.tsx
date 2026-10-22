import { useState } from "react";
import { Link, useParams, useSearch } from "@tanstack/react-router";
import { AlertTriangle, ChevronLeft, ChevronRight, ExternalLink, ShieldCheck } from "lucide-react";

import { ErrorState, LoadingState, SectionTitle, StatusMark } from "../components/cms/shared";
import { Button } from "../components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { apiSummaryToMeasure, formatApiDate, labelField } from "../features/measures/api/adapters";
import { useApiMeasure, useApiMeasureList } from "../features/measures/api/queries";
import type { EvidenceReference, MeasureVersion } from "../features/measures/api/types";
import { parseDemoFilters } from "../features/measures/demo/filters";

function valueFor(version: MeasureVersion | undefined, fieldName: string) {
  return version?.fields.find((field) => field.field === fieldName);
}

function EvidenceList({ versions }: { versions: MeasureVersion[] }) {
  const references = new Map<string, EvidenceReference>();
  versions.forEach((version) =>
    version.fields.forEach((field) =>
      field.evidence.forEach((reference) => references.set(reference.evidence_id, reference)),
    ),
  );

  return (
    <section className="api-evidence-section">
      <SectionTitle demo={false}>Approved source evidence</SectionTitle>
      {references.size === 0 ? (
        <p className="unavailable-text">
          No public evidence reference is available for the selected versions.
        </p>
      ) : (
        <div className="api-evidence-list">
          {[...references.values()].map((reference) => (
            <article key={reference.evidence_id}>
              <div>
                <span className="quiet-label font-mono">{reference.source_revision_id}</span>
                <h3>{reference.document_title}</h3>
              </div>
              <p>{reference.excerpt}</p>
              <div className="evidence-meta">
                <span>{reference.locator ?? "Source locator unavailable"}</span>
                <a href={reference.official_url} target="_blank" rel="noreferrer">
                  Open source <ExternalLink size={12} />
                </a>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

export function ApiMeasureDetailPage() {
  const params = useParams({ strict: false });
  const rawSearch = useSearch({ strict: false });
  const filters = parseDemoFilters(rawSearch);
  const measureId = typeof params.measureId === "string" ? params.measureId : "";
  const [tab, setTab] = useState("changes");
  const detailQuery = useApiMeasure(measureId, filters);
  const listQuery = useApiMeasureList(filters);

  if (detailQuery.isPending || listQuery.isPending) {
    return <LoadingState label="Loading approved measure evidence…" />;
  }
  if (detailQuery.isError || listQuery.isError) {
    const error = detailQuery.error ?? listQuery.error;
    return (
      <ErrorState
        message={error?.message ?? "The public measure API request failed."}
        onRetry={() =>
          void (detailQuery.isError ? detailQuery.refetch() : listQuery.refetch())
        }
      />
    );
  }

  const measure = detailQuery.data;
  const results = listQuery.data.items;
  const index = results.findIndex((candidate) => candidate.measure_id === measure.measure_id);
  const previous = index > 0 ? results[index - 1] : undefined;
  const next = index >= 0 ? results[index + 1] : undefined;
  const availableFields = [...new Set(measure.versions.flatMap((version) => version.fields.map((field) => field.field)))];

  return (
    <div className="visual-page detail-page">
      <div className="detail-navigation">
        <nav aria-label="Breadcrumb">
          <Link to="/" search={filters}>Dashboard</Link>
          <ChevronRight size={12} />
          <Link to="/measures" search={filters}>Measures</Link>
          <ChevronRight size={12} />
          <span className="font-mono">{measure.measure_id}</span>
        </nav>
        <div className="previous-next">
          <Button asChild={Boolean(previous)} variant="ghost" size="sm" disabled={!previous}>
            {previous ? (
              <Link to="/measures/$measureId" params={{ measureId: previous.measure_id }} search={filters}>
                <ChevronLeft /> Previous <span className="font-mono neighbor-id">{previous.measure_id}</span>
              </Link>
            ) : <span><ChevronLeft size={14} /> Previous</span>}
          </Button>
          <span className="quiet-label">
            {index >= 0 ? `${index + 1} of ${results.length}` : "Outside filtered results"}
          </span>
          <Button asChild={Boolean(next)} variant="ghost" size="sm" disabled={!next}>
            {next ? (
              <Link to="/measures/$measureId" params={{ measureId: next.measure_id }} search={filters}>
                Next <span className="font-mono neighbor-id">{next.measure_id}</span> <ChevronRight />
              </Link>
            ) : <span>Next <ChevronRight size={14} /></span>}
          </Button>
        </div>
      </div>

      <header className="detail-header">
        <div className="measure-kicker">{measure.measure_id}</div>
        <h1>{measure.name}</h1>
        <div className="metadata-strip">
          <div><span>Approved change state</span><StatusMark status={measure.change_status} /></div>
          <div><span>Verification</span><strong>{apiSummaryToMeasure(measure).review}</strong></div>
          <div><span>Last verified</span><strong>{formatApiDate(measure.freshness.last_verified_at)}</strong></div>
          <div><span>Source checked</span><strong>{formatApiDate(measure.freshness.last_source_check_at)}</strong></div>
          <div><span>Published years</span><strong>{measure.performance_years.map((year) => `PY${year}`).join(", ")}</strong></div>
          <span className="api-data-badge"><ShieldCheck size={12} /> Public API</span>
        </div>
      </header>

      <Tabs value={tab} onValueChange={setTab} className="detail-tabs">
        <TabsList aria-label="Measure sections" className="measure-tabs-list">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="changes">Versions</TabsTrigger>
          <TabsTrigger value="impact">AI Impact</TabsTrigger>
          <TabsTrigger value="history">Source status</TabsTrigger>
        </TabsList>

        <TabsContent value="changes">
          <section className="comparison-section">
            <SectionTitle demo={false}>Published version fields</SectionTitle>
            <div className="m1-boundary-note">
              <AlertTriangle size={16} />
              <p>
                C1 shows approved version records and availability states. Production field-level
                change classification remains out of scope until C2; missing text is never treated
                as a removal.
              </p>
            </div>
            <div className="comparison-table" role="table" aria-label="Published version fields">
              <div className="comparison-row comparison-header" role="row">
                <div role="columnheader">Field</div>
                {measure.versions.map((version) => <div key={version.version_id} role="columnheader">PY{version.performance_year}</div>)}
              </div>
              {availableFields.map((fieldName) => (
                <div className="comparison-row" role="row" key={fieldName}>
                  <div className="field-label" role="cell"><strong>{labelField(fieldName)}</strong></div>
                  {measure.versions.map((version) => {
                    const field = valueFor(version, fieldName);
                    return (
                      <div className="spec-text" role="cell" key={version.version_id}>
                        <span className="mobile-year">PY{version.performance_year}</span>
                        {field?.availability === "available" ? field.value : (
                          <span className="unavailable-text">
                            {field ? `${field.availability} in approved evidence` : "Not represented in this version"}
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          </section>
          <EvidenceList versions={measure.versions} />
        </TabsContent>

        <TabsContent value="overview">
          <section className="overview-section">
            <SectionTitle demo={false}>Measure overview</SectionTitle>
            <p className="overview-description">{measure.description}</p>
            <dl className="overview-facts">
              <div><dt>Measure ID</dt><dd className="font-mono">{measure.measure_id}</dd></div>
              <div><dt>Change state</dt><dd>{measure.change_status}</dd></div>
              <div><dt>Affected fields</dt><dd>{measure.affected_fields.map(labelField).join(", ") || "None approved"}</dd></div>
              <div><dt>Version records</dt><dd>{measure.versions.length}</dd></div>
            </dl>
          </section>
          <EvidenceList versions={measure.versions} />
        </TabsContent>

        <TabsContent value="impact">
          <section className="impact-section demo-only-panel">
            <SectionTitle>AI impact prototype not connected</SectionTitle>
            <p>
              This interaction is an M2 prototype. C1 does not call an AI service or generate
              production guidance from the public API record.
            </p>
          </section>
        </TabsContent>

        <TabsContent value="history">
          <section className="history-section">
            <SectionTitle demo={false}>Public source status</SectionTitle>
            <dl className="overview-facts">
              <div><dt>Verification state</dt><dd>{measure.freshness.verification_status.replaceAll("_", " ")}</dd></div>
              <div><dt>Last verified</dt><dd>{formatApiDate(measure.freshness.last_verified_at)}</dd></div>
              <div><dt>Last source check</dt><dd>{formatApiDate(measure.freshness.last_source_check_at)}</dd></div>
              <div><dt>Newer revision detected</dt><dd>{measure.freshness.newer_revision_detected ? "Yes" : "No"}</dd></div>
            </dl>
            <p className="section-subtext">Internal review notes and draft workflow metadata are intentionally excluded.</p>
          </section>
        </TabsContent>
      </Tabs>
    </div>
  );
}
