import { useEffect, useState, type FormEvent } from "react";
import { Link } from "@tanstack/react-router";
import {
  Archive,
  ArrowLeft,
  CheckCircle2,
  ChevronDown,
  ExternalLink,
  FileText,
  Plus,
  RefreshCw,
  RotateCcw,
  ShieldAlert,
  Sparkles,
} from "lucide-react";

import { ErrorState, LoadingState } from "../components/cms/shared";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import {
  useAdminSession,
  useAdminFieldClarification,
  useAdminIngestionRunCreate,
  useAdminIngestionRuns,
  useAdminSourceCheck,
  useAdminSourceCreate,
  useAdminSourceNormalization,
  useAdminSourceNormalizationDetail,
  useAdminSources,
  useAdminSourceUpdate,
  type AdminIngestionRun,
  type AdminIngestionStage,
  type AdminSourceCreate,
} from "../features/admin/api";

const emptySource: AdminSourceCreate = {
  source_id: "",
  title: "",
  official_url: "",
  source_format: "html",
  notes: null,
};

function formatDate(value: string | null) {
  if (!value) return "Never";
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}

function runStatusLabel(status: AdminIngestionRun["status"]) {
  return {
    running: "Checking official sources",
    completed: "Check complete",
    completed_with_errors: "Complete with errors",
    interrupted: "Check interrupted",
  }[status];
}

function stageLabel(stage: AdminIngestionStage) {
  return {
    pending: "Queued",
    downloading: "Downloading",
    extracting: "Extracting",
    comparing: "Comparing",
    awaiting_verification: "Awaiting verification",
    unchanged: "Unchanged",
    failed: "Failed",
  }[stage];
}

export function AdminSourcesPage() {
  const session = useAdminSession();
  const sources = useAdminSources(Boolean(session.data?.authenticated));
  const refetchSources = sources.refetch;
  const ingestionRuns = useAdminIngestionRuns(Boolean(session.data?.authenticated));
  const createIngestionRun = useAdminIngestionRunCreate();
  const createSource = useAdminSourceCreate();
  const updateSource = useAdminSourceUpdate();
  const checkSource = useAdminSourceCheck();
  const normalizeSource = useAdminSourceNormalization();
  const clarifyField = useAdminFieldClarification();
  const [draft, setDraft] = useState<AdminSourceCreate>(emptySource);
  const [showForm, setShowForm] = useState(false);
  const [openNormalizationId, setOpenNormalizationId] = useState<string | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const normalization = useAdminSourceNormalizationDetail(
    openNormalizationId,
    Boolean(session.data?.authenticated),
  );
  const runs = ingestionRuns.data?.items ?? [];
  const latestRun = runs[0];
  const activeRun = runs.find((run) => run.status === "running");
  const displayedRun = runs.find((run) => run.run_id === selectedRunId) ?? latestRun;

  useEffect(() => {
    if (latestRun?.completed_at) {
      void refetchSources();
    }
  }, [latestRun?.completed_at, latestRun?.run_id, refetchSources]);

  if (session.isPending) return <LoadingState label="Checking administrator access…" />;
  if (session.isError) {
    return <ErrorState message={session.error.message} onRetry={() => void session.refetch()} />;
  }
  if (!session.data.authenticated) {
    return (
      <div className="empty-state admin-source-auth">
        <ShieldAlert aria-hidden="true" />
        <h1>Administrator sign-in required</h1>
        <p>Source registration and retrieval history are private operational data.</p>
        <Link to="/admin" search={{}}>Return to the review desk</Link>
      </div>
    );
  }
  if (sources.isPending) return <LoadingState label="Loading the CMS source registry…" />;
  if (sources.isError) {
    return <ErrorState message={sources.error.message} onRetry={() => void sources.refetch()} />;
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    createSource.mutate(draft, {
      onSuccess: () => {
        setDraft(emptySource);
        setShowForm(false);
      },
    });
  }

  return (
    <div className="visual-page admin-page admin-sources-page">
      <Link to="/admin" search={{}} className="admin-back-link">
        <ArrowLeft aria-hidden="true" /> Review desk
      </Link>

      <header className="admin-page-header admin-source-header">
        <div>
          <p className="page-eyebrow">Protected evidence operations</p>
          <h1>CMS source registry</h1>
          <p>
            Register official CMS documents, preserve every retrieved revision, and inspect
            extraction status before any field enters human review.
          </p>
        </div>
        <div className="admin-source-header-actions">
          <Button
            variant="outline"
            disabled={
              createIngestionRun.isPending || Boolean(activeRun) || sources.data.items.length === 0
            }
            onClick={() =>
              createIngestionRun.mutate(undefined, {
                onSuccess: (run) => setSelectedRunId(run.run_id),
              })
            }
          >
            <RefreshCw className={activeRun ? "is-spinning" : undefined} aria-hidden="true" />
            {createIngestionRun.isPending || activeRun ? "Checking sources…" : "Check for updates"}
          </Button>
          <Button onClick={() => setShowForm((value) => !value)}>
            <Plus aria-hidden="true" /> {showForm ? "Close form" : "Register source"}
          </Button>
        </div>
      </header>

      <div className="admin-boundary-note admin-source-boundary" role="note">
        <ShieldAlert aria-hidden="true" /> Only HTTPS URLs on cms.gov are accepted. Fetching a
        source creates private evidence history; it never publishes measure data.
      </div>

      {ingestionRuns.isError && (
        <p className="admin-form-error" role="alert">{ingestionRuns.error.message}</p>
      )}
      {displayedRun && (
        <section
          className={`surface-card ingestion-run-ledger ${displayedRun.status}`}
          aria-label="Ingestion run progress"
          aria-live={displayedRun.status === "running" ? "polite" : "off"}
        >
          <header>
            <div>
              <p className="card-kicker">Ingestion run</p>
              <h2>{runStatusLabel(displayedRun.status)}</h2>
            </div>
            <div className="ingestion-run-controls">
              {runs.length > 1 && (
                <label>
                  <span>Run history</span>
                  <select
                    value={displayedRun.run_id}
                    onChange={(event) => setSelectedRunId(event.target.value)}
                  >
                    {runs.map((run) => (
                      <option key={run.run_id} value={run.run_id}>
                        {formatDate(run.started_at)} · {runStatusLabel(run.status)}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              <span className={`ingestion-run-state ${displayedRun.status}`}>
                {runStatusLabel(displayedRun.status)}
              </span>
            </div>
          </header>
          <div className="ingestion-run-summary">
            <div>
              <span>{displayedRun.completed_count} of {displayedRun.source_count} sources</span>
              <span>{displayedRun.failed_count} failed</span>
            </div>
            <progress
              value={displayedRun.completed_count}
              max={Math.max(displayedRun.source_count, 1)}
              aria-label={`${displayedRun.completed_count} of ${displayedRun.source_count} sources complete`}
            />
            <div className="ingestion-run-times">
              <span>Started <time dateTime={displayedRun.started_at}>{formatDate(displayedRun.started_at)}</time></span>
              <span>
                {displayedRun.completed_at ? (
                  <>Finished <time dateTime={displayedRun.completed_at}>{formatDate(displayedRun.completed_at)}</time></>
                ) : (
                  "Processing now"
                )}
              </span>
            </div>
          </div>
          {displayedRun.status === "interrupted" && (
            <p className="ingestion-run-notice" role="alert">
              Processing stopped before every queued source finished. The last recorded document
              stage remains below for investigation.
            </p>
          )}
          <ol className="ingestion-run-items">
            {displayedRun.items.map((item) => (
              <li key={item.item_id} className={item.stage}>
                <div className="ingestion-item-heading">
                  <div>
                    <strong>{item.source_id}</strong>
                    <span>{item.source_title}</span>
                  </div>
                  <span className={`ingestion-stage-badge ${item.stage}`}>
                    {stageLabel(item.stage)}
                  </span>
                </div>
                <div className="ingestion-item-times">
                  <span>Started {formatDate(item.started_at)}</span>
                  <span>{item.completed_at ? `Finished ${formatDate(item.completed_at)}` : "Not finished"}</span>
                </div>
                <div className="ingestion-stage-trail" aria-label={`${item.source_id} processing history`}>
                  {item.events.map((event) => (
                    <div key={event.event_id} className="ingestion-stage-event">
                      <span>{stageLabel(event.stage)}</span>
                      <time dateTime={event.occurred_at}>{formatDate(event.occurred_at)}</time>
                      {event.detail && <small>{event.detail}</small>}
                    </div>
                  ))}
                </div>
                {item.error && <p className="ingestion-item-error" role="alert">{item.error}</p>}
              </li>
            ))}
          </ol>
        </section>
      )}

      {showForm && (
        <form className="surface-card admin-source-form" onSubmit={submit}>
          <div>
            <p className="card-kicker">New official source</p>
            <h2>Registry details</h2>
          </div>
          <label>
            <span>Source ID</span>
            <Input
              value={draft.source_id}
              placeholder="CMS-PY2026-APP-REQ"
              pattern="[A-Z0-9][A-Z0-9_-]{2,99}"
              onChange={(event) =>
                setDraft((value) => ({ ...value, source_id: event.target.value.toUpperCase() }))
              }
              required
            />
          </label>
          <label>
            <span>Document title</span>
            <Input
              value={draft.title}
              onChange={(event) => setDraft((value) => ({ ...value, title: event.target.value }))}
              required
            />
          </label>
          <label className="admin-source-url-field">
            <span>Official CMS URL</span>
            <Input
              type="url"
              value={draft.official_url}
              placeholder="https://www.cms.gov/..."
              onChange={(event) =>
                setDraft((value) => ({ ...value, official_url: event.target.value }))
              }
              required
            />
          </label>
          <label>
            <span>Document format</span>
            <select
              value={draft.source_format}
              onChange={(event) =>
                setDraft((value) => ({
                  ...value,
                  source_format: event.target.value as "html" | "pdf",
                }))
              }
            >
              <option value="html">HTML page</option>
              <option value="pdf">PDF document</option>
            </select>
          </label>
          <label className="admin-source-notes-field">
            <span>Internal notes (optional)</span>
            <textarea
              value={draft.notes ?? ""}
              onChange={(event) =>
                setDraft((value) => ({ ...value, notes: event.target.value || null }))
              }
            />
          </label>
          {createSource.isError && (
            <p className="admin-form-error" role="alert">{createSource.error.message}</p>
          )}
          <Button type="submit" disabled={createSource.isPending}>
            {createSource.isPending ? "Registering…" : "Add to private registry"}
          </Button>
        </form>
      )}

      <section className="admin-source-list" aria-label="Registered CMS sources">
        {sources.data.items.map((source) => {
          const mutationPending =
            updateSource.isPending ||
            checkSource.isPending ||
            normalizeSource.isPending ||
            clarifyField.isPending;
          const normalizationId =
            source.latest_revision?.extraction?.normalization?.normalization_id ?? null;
          const isNormalizationOpen =
            normalizationId !== null && normalizationId === openNormalizationId;
          return (
            <article className="surface-card admin-source-card" key={source.source_id}>
              <header>
                <div>
                  <span className="admin-measure-id">{source.source_id}</span>
                  <h2>{source.title}</h2>
                </div>
                <span className={`private-state ${source.is_active ? "active" : "inactive"}`}>
                  {source.is_active ? <CheckCircle2 aria-hidden="true" /> : <Archive aria-hidden="true" />}
                  {source.is_active ? "Active" : "Inactive"}
                </span>
              </header>
              <a href={source.official_url} target="_blank" rel="noreferrer" className="admin-source-url">
                {source.official_url} <ExternalLink aria-hidden="true" />
              </a>
              {source.notes && <p className="admin-source-notes">{source.notes}</p>}

              <dl className="admin-source-facts">
                <div>
                  <dt>Format</dt>
                  <dd><FileText aria-hidden="true" /> {source.source_format.toUpperCase()}</dd>
                </div>
                <div>
                  <dt>Revisions</dt>
                  <dd>{source.revision_count}</dd>
                </div>
                <div>
                  <dt>Latest check</dt>
                  <dd>{formatDate(source.latest_check?.checked_at ?? null)}</dd>
                </div>
                <div>
                  <dt>Outcome</dt>
                  <dd>{source.latest_check?.outcome.replace("_", " ") ?? "Not fetched"}</dd>
                </div>
              </dl>

              {source.latest_revision?.extraction && (
                <div className="admin-source-extraction">
                  <strong>{source.latest_revision.extraction.status.replace("_", " ")}</strong>
                  <span>
                    Revision {source.latest_revision.revision_number} · {source.latest_revision.extraction.segment_count}
                    {" "}text segments
                    {source.latest_revision.extraction.normalization && (
                      <> · {source.latest_revision.extraction.normalization.staged_field_count} staged fields</>
                    )}
                    {" "}· SHA-256 {source.latest_revision.content_hash.slice(0, 12)}…
                  </span>
                </div>
              )}
              {source.latest_check?.error && (
                <p className="admin-form-error" role="alert">{source.latest_check.error}</p>
              )}

              <footer>
                <Button
                  variant="outline"
                  disabled={mutationPending || !source.is_active}
                  onClick={() => checkSource.mutate({ sourceId: source.source_id, force: false })}
                >
                  <RefreshCw aria-hidden="true" /> Check source
                </Button>
                <Button
                  variant="outline"
                  disabled={mutationPending || !source.is_active || source.revision_count === 0}
                  onClick={() => checkSource.mutate({ sourceId: source.source_id, force: true })}
                >
                  <RotateCcw aria-hidden="true" /> Force re-extract
                </Button>
                <Button
                  variant="outline"
                  disabled={
                    mutationPending ||
                    source.latest_revision?.extraction?.status !== "extracted" ||
                    Boolean(source.latest_revision?.extraction?.normalization)
                  }
                  onClick={() => {
                    const extractionId = source.latest_revision?.extraction?.extraction_id;
                    if (extractionId) normalizeSource.mutate(extractionId);
                  }}
                >
                  Normalize candidates
                </Button>
                {normalizationId && (
                  <Button
                    variant="outline"
                    disabled={mutationPending}
                    aria-expanded={isNormalizationOpen}
                    onClick={() =>
                      setOpenNormalizationId(isNormalizationOpen ? null : normalizationId)
                    }
                  >
                    <ChevronDown aria-hidden="true" /> Inspect candidates
                  </Button>
                )}
                <Button
                  variant="outline"
                  disabled={mutationPending}
                  onClick={() =>
                    updateSource.mutate({ sourceId: source.source_id, isActive: !source.is_active })
                  }
                >
                  {source.is_active ? "Deactivate" : "Reactivate"}
                </Button>
              </footer>
              {isNormalizationOpen && (
                <section className="admin-normalization-panel" aria-label="Normalized candidates">
                  {normalization.isPending && <LoadingState label="Loading candidates…" />}
                  {normalization.isError && (
                    <p className="admin-form-error" role="alert">
                      {normalization.error.message}
                    </p>
                  )}
                  {normalization.data?.candidates.map((candidate) => (
                    <div className="admin-normalized-candidate" key={candidate.candidate_id}>
                      <header>
                        <strong>
                          {candidate.specification_identifier_candidate ??
                            candidate.measure_id_candidate ??
                            "Unresolved identity"}
                        </strong>
                        <span>{candidate.identity_status.replace("_", " ")}</span>
                      </header>
                      {candidate.fields
                        .filter((field) => field.status === "unresolved")
                        .map((field) => {
                          const latest = field.clarifications[0];
                          return (
                            <article
                              className="admin-clarification-field"
                              key={field.field_candidate_id}
                            >
                              <div>
                                <strong>{field.field_name.replaceAll("_", " ")}</strong>
                                {latest && (
                                  <span className={`clarification-outcome ${latest.outcome}`}>
                                    {latest.outcome}
                                  </span>
                                )}
                              </div>
                              <Button
                                variant="outline"
                                disabled={mutationPending}
                                onClick={() => clarifyField.mutate(field.field_candidate_id)}
                              >
                                <Sparkles aria-hidden="true" /> Clarify with AI
                              </Button>
                              {latest && (
                                <div className="admin-clarification-result">
                                  {latest.proposed_value && <blockquote>{latest.proposed_value}</blockquote>}
                                  <p>{latest.summary}</p>
                                  <ul>
                                    {latest.evidence.map((evidence) => (
                                      <li key={evidence.evidence_id}>
                                        <a href={evidence.official_url} target="_blank" rel="noreferrer">
                                          {evidence.source_title} · {evidence.locator}
                                        </a>
                                        <span>{evidence.relation}</span>
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                            </article>
                          );
                        })}
                    </div>
                  ))}
                </section>
              )}
            </article>
          );
        })}
      </section>
      {sources.data.items.length === 0 && !showForm && (
        <div className="empty-state surface-card">No official CMS sources are registered yet.</div>
      )}
      {(checkSource.isError ||
        createIngestionRun.isError ||
        updateSource.isError ||
        normalizeSource.isError ||
        clarifyField.isError) && (
        <p className="admin-form-error admin-source-mutation-error" role="alert">
          {(
            checkSource.error ??
            createIngestionRun.error ??
            updateSource.error ??
            normalizeSource.error ??
            clarifyField.error
          )?.message}
        </p>
      )}
    </div>
  );
}
