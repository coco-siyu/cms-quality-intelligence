import { useState } from "react";
import { Link, useParams, useSearch } from "@tanstack/react-router";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock,
  Sparkles,
} from "lucide-react";

import { EvidencePanel } from "../components/cms/EvidencePanel";
import { DemoBadge, LoadingState, SectionTitle, StatusMark } from "../components/cms/shared";
import { Button } from "../components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { comparisonStatus, parseDemoFilters } from "../features/measures/demo/filters";
import { useDemoMeasure, useDemoMeasureList } from "../features/measures/demo/queries";
import type { DemoMeasure, DemoSpecField } from "../features/measures/demo/types";
import { getDataMode } from "../features/measures/dataMode";
import { ApiMeasureDetailPage } from "./ApiMeasureDetailPage";

function DiffText({ field, year }: { field: DemoSpecField; year: number }) {
  const text = year === 2025 ? field.before : field.after;
  const highlight = year === 2025 ? field.removed : field.added;
  if (!highlight || !text.includes(highlight)) return <>{text}</>;

  const position = text.indexOf(highlight);
  return (
    <>
      {text.slice(0, position)}
      {year === 2025 ? <del>{highlight}</del> : <ins>{highlight}</ins>}
      {text.slice(position + highlight.length)}
    </>
  );
}

function Comparison({ measure, from, to }: { measure: DemoMeasure; from: string; to: string }) {
  return (
    <section className="comparison-section">
      <SectionTitle demo={false}>
        Specification, PY{from} and PY{to}
      </SectionTitle>
      <div className="diff-key">
        <span>
          <span className="diff-key-add">+</span> Addition
        </span>
        <span>
          <span className="diff-key-remove">−</span> Deletion
        </span>
      </div>
      <div className="comparison-table" role="table" aria-label="Year specification comparison">
        <div className="comparison-row comparison-header" role="row">
          <div role="columnheader">Field</div>
          <div role="columnheader">PY{from}</div>
          <div role="columnheader">PY{to}</div>
        </div>
        {measure.specs.map((field) => {
          const changed = from !== to && field.before !== field.after && !field.unavailable;
          const missing = field.unavailable && (from === "2026" || to === "2026");
          return (
            <div key={field.name} className={`comparison-row ${changed ? "changed-row" : ""}`} role="row">
              <div className="field-label" role="cell">
                <strong>{field.name}</strong>
                {missing ? (
                  <span className="unavailable-text">Unavailable in fictional source</span>
                ) : (
                  <StatusMark
                    status={
                      changed
                        ? measure.status === "added" || measure.status === "removed"
                          ? measure.status
                          : "modified"
                        : "unchanged"
                    }
                  />
                )}
              </div>
              {[from, to].map((year) => (
                <div
                  key={year}
                  role="cell"
                  className={`spec-text ${!changed ? "unchanged-text" : ""} ${
                    field.unavailable && year === "2026" ? "missing-field" : ""
                  }`}
                >
                  <span className="mobile-year">PY{year}</span>
                  <DiffText field={field} year={Number(year)} />
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </section>
  );
}

function DemoMeasureDetailPage() {
  const params = useParams({ strict: false });
  const rawSearch = useSearch({ strict: false });
  const filters = parseDemoFilters(rawSearch);
  const measureId = typeof params.measureId === "string" ? params.measureId : "";
  const [role, setRole] = useState<"analyst" | "manager">("analyst");
  const [tab, setTab] = useState("changes");
  const measureQuery = useDemoMeasure(measureId);
  const resultQuery = useDemoMeasureList(filters);

  if (!measureQuery.isFetched || !resultQuery.data) {
    return <LoadingState label="Loading fictional measure…" />;
  }

  const measure = measureQuery.data;
  if (!measure) {
    return (
      <div className="empty-state">
        <h1>Measure not found</h1>
        <Button asChild variant="link">
          <Link to="/" search={filters}>
            Back to measures
          </Link>
        </Button>
      </div>
    );
  }

  const results = resultQuery.data.items;
  const index = results.findIndex((candidate) => candidate.id === measure.id);
  const previous = index > 0 ? results[index - 1] : undefined;
  const next = index >= 0 ? results[index + 1] : undefined;
  const warning = measure.review === "Needs re-verification";

  return (
    <>
      <div className="detail-navigation">
        <nav aria-label="Breadcrumb">
          <Link to="/" search={filters}>
            Dashboard
          </Link>
          <ChevronRight size={12} />
          <Link to="/measures" search={filters}>
            Measures
          </Link>
          <ChevronRight size={12} />
          <span className="font-mono">{measure.id}</span>
        </nav>
        <div className="previous-next">
          <Button
            asChild={Boolean(previous)}
            variant="ghost"
            size="sm"
            disabled={!previous}
            aria-label="Previous measure"
          >
            {previous ? (
              <Link
                to="/measures/$measureId"
                params={{ measureId: previous.id }}
                search={filters}
              >
                <ChevronLeft /> Previous <span className="font-mono neighbor-id">{previous.id}</span>
              </Link>
            ) : (
              <span>
                <ChevronLeft size={14} /> Previous
              </span>
            )}
          </Button>
          <span className="quiet-label">
            {index >= 0 ? `${index + 1} of ${results.length}` : "Outside filtered results"}
          </span>
          <Button
            asChild={Boolean(next)}
            variant="ghost"
            size="sm"
            disabled={!next}
            aria-label="Next measure"
          >
            {next ? (
              <Link to="/measures/$measureId" params={{ measureId: next.id }} search={filters}>
                Next <span className="font-mono neighbor-id">{next.id}</span> <ChevronRight />
              </Link>
            ) : (
              <span>
                Next <ChevronRight size={14} />
              </span>
            )}
          </Button>
        </div>
      </div>

      <header className="detail-header">
        <div className="measure-kicker">{measure.id}</div>
        <h1>{measure.name}</h1>
        <div className="metadata-strip">
          <div>
            <span>Change</span>
            <StatusMark status={comparisonStatus(measure, filters)} />
          </div>
          <div>
            <span>Prototype verification</span>
            <strong className={warning ? "warning-text" : ""}>
              {warning && <AlertTriangle size={13} />} {measure.review}
            </strong>
          </div>
          <div>
            <span>Fictional verified date</span>
            <strong>{measure.verified}</strong>
          </div>
          <div>
            <span>Program context</span>
            <strong>MSSP, APP Plus</strong>
          </div>
          <div>
            <span>Prototype years</span>
            <strong>{measure.years.map((year) => `PY${year}`).join(", ")}</strong>
          </div>
          <DemoBadge />
        </div>
      </header>

      <Tabs value={tab} onValueChange={setTab} className="detail-tabs">
        <TabsList aria-label="Measure sections" className="measure-tabs-list">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="changes">Changes</TabsTrigger>
          <TabsTrigger value="impact">AI Impact</TabsTrigger>
          <TabsTrigger value="history">Review History</TabsTrigger>
        </TabsList>

        {warning && (
          <div className="warning-callout" role="alert">
            <AlertTriangle size={18} />
            <p>
              <strong>Needs re-verification.</strong> The fictional PY2026 exclusion text does not
              cleanly match its prototype excerpt.
            </p>
          </div>
        )}

        <TabsContent value="changes">
          <Comparison measure={measure} from={filters.from} to={filters.to} />
          <EvidencePanel measure={measure} />
        </TabsContent>

        <TabsContent value="overview">
          <section className="overview-section">
            <SectionTitle demo={false}>Measure overview</SectionTitle>
            <p className="overview-description">{measure.description}</p>
            <dl className="overview-facts">
              <div>
                <dt>Measure ID</dt>
                <dd className="font-mono">{measure.id}</dd>
              </div>
              <div>
                <dt>Affected field</dt>
                <dd>{measure.field}</dd>
              </div>
              <div>
                <dt>Prototype applicability</dt>
                <dd>{measure.years.map((year) => `PY${year}`).join(" · ")}</dd>
              </div>
              <div>
                <dt>Prototype source check</dt>
                <dd>Oct 14, 2026</dd>
              </div>
            </dl>
            <h3>Fictional normalized specifications</h3>
            {measure.specs.map((field) => (
              <div key={field.name} className="overview-spec">
                <strong>{field.name}</strong>
                <p className="spec-text">
                  {measure.years.includes(2026) ? field.after : field.before}
                </p>
              </div>
            ))}
          </section>
          <EvidencePanel measure={measure} />
        </TabsContent>

        <TabsContent value="impact">
          <section className="impact-section">
            <div className="section-heading-row">
              <SectionTitle demo={false}>Potential impact</SectionTitle>
              <div className="role-switch" role="group" aria-label="Explanation role">
                <Button
                  variant="ghost"
                  aria-pressed={role === "analyst"}
                  onClick={() => setRole("analyst")}
                >
                  Data Analyst
                </Button>
                <Button
                  variant="ghost"
                  aria-pressed={role === "manager"}
                  onClick={() => setRole("manager")}
                >
                  ACO Quality Manager
                </Button>
              </div>
            </div>
            <div className="ai-disclaimer">
              <Sparkles size={16} />
              <span>Fictional AI-style copy · Possible implications, not CMS policy</span>
            </div>
            {warning && (
              <p className="impact-caveat">
                This fictional exclusion change is unresolved. Do not use it to update reporting
                logic or workflows.
              </p>
            )}
            <h3>What changed</h3>
            <p>
              {measure.status === "modified"
                ? `The prototype comparison identifies a fictional change to the ${measure.field.toLowerCase()} between PY2025 and PY2026.`
                : measure.status === "added"
                  ? "This fictional measure is included in the PY2026 prototype set, but not PY2025."
                  : measure.status === "removed"
                    ? "This fictional measure appears only in the PY2025 prototype set."
                    : "No substantive year-over-year change appears in this fictional example."}
            </p>
            <h3>Why it may matter</h3>
            <p>
              {role === "analyst"
                ? `Review the ${measure.field === "No change" ? "existing" : measure.field.toLowerCase()} mapping, calculation assumptions, and validation cases after authoritative evidence is available.`
                : "Coordinate with clinical, reporting, and quality teams only after authoritative requirements have been verified."}
            </p>
            <h3>Review considerations</h3>
            <ul className="impact-list">
              {(role === "analyst"
                ? [
                    "Compare source-backed definitions before changing calculations.",
                    "Validate the affected population against representative test cases.",
                    "Document year-specific assumptions in downstream dashboards.",
                  ]
                : [
                    "Confirm the applicable reporting-year measure set.",
                    "Discuss possible workflow changes with clinical and operations teams.",
                    "Schedule follow-up after source verification.",
                  ]
              ).map((item) => (
                <li key={item}>
                  <ArrowRight size={14} /> {item}
                </li>
              ))}
            </ul>
            <p className="quiet-label">
              Fictional evidence reference: DEMO-{measure.id}-2026-v1 · No AI service connected
            </p>
          </section>
          <EvidencePanel measure={measure} />
        </TabsContent>

        <TabsContent value="history">
          <section className="history-section">
            <SectionTitle>Verification and publication history</SectionTitle>
            <p className="section-subtext">
              Fictional public timeline · No internal review records are represented
            </p>
            <ol className="history-timeline">
              {[
                {
                  date: "Oct 14, 2026",
                  title: "Prototype source check recorded",
                  body: "A fictional revision was checked. This does not establish regulatory currency.",
                  icon: Clock,
                },
                {
                  date: measure.verified,
                  title: warning ? "Re-verification required" : "Prototype comparison approved",
                  body: warning
                    ? "A fictional exclusion excerpt requires review."
                    : "Fictional specifications were compared for PY2025 and PY2026.",
                  icon: warning ? AlertTriangle : CheckCircle2,
                },
                {
                  date: "Sep 18, 2026",
                  title: "Fictional PY2026 revision registered",
                  body: `Prototype revision DEMO-${measure.id}-2026-v1.`,
                  icon: Clock,
                },
              ].map((event) => (
                <li key={`${event.date}-${event.title}`}>
                  <span className="history-dot">
                    <event.icon size={16} />
                  </span>
                  <div>
                    <time>{event.date}</time>
                    <h3>{event.title}</h3>
                    <p>{event.body}</p>
                  </div>
                </li>
              ))}
            </ol>
          </section>
        </TabsContent>
      </Tabs>
    </>
  );
}

export function MeasureDetailPage() {
  return getDataMode() === "demo" ? <DemoMeasureDetailPage /> : <ApiMeasureDetailPage />;
}
