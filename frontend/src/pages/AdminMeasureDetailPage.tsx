import { useState, type FormEvent } from "react";
import { Link, useParams } from "@tanstack/react-router";
import {
  ArrowLeft,
  Ban,
  Check,
  ExternalLink,
  History,
  LockKeyhole,
  PencilLine,
} from "lucide-react";

import { ErrorState, LoadingState } from "../components/cms/shared";
import { Button } from "../components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "../components/ui/dialog";
import {
  useAdminCandidateReview,
  useAdminMeasure,
  useAdminSession,
  type AdminCandidateDecision,
  type AdminFieldCandidate,
} from "../features/admin/api";
import { AdminWorkspacePage } from "./AdminWorkspacePage";

const collectionLabels: Record<string, string> = {
  program_roster: "Program roster",
  ecqm: "eCQM",
  mips_cqm: "MIPS CQM",
  medicare_cqm: "Medicare CQM",
  cahps_survey: "CAHPS for MIPS Survey",
  administrative_claims: "Administrative claims",
};

const decisionLabels = {
  pending: "Pending",
  approve: "Approved",
  needs_revision: "Needs revision",
  not_applicable: "Not applicable",
} as const;

function formatReviewDate(value: string) {
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function CandidateReviewDialog({
  candidate,
  measureId,
  open,
  onOpenChange,
}: {
  candidate: AdminFieldCandidate;
  measureId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const currentDecision = candidate.review_decision === "pending"
    ? "approve"
    : candidate.review_decision;
  const [decision, setDecision] = useState<AdminCandidateDecision["decision"]>(currentDecision);
  const [reviewedValue, setReviewedValue] = useState(
    candidate.reviewed_value ?? candidate.candidate_value,
  );
  const [reviewerNotes, setReviewerNotes] = useState(candidate.reviewer_notes ?? "");
  const mutation = useAdminCandidateReview(measureId);
  const needsNotes = decision !== "approve";
  const formIsValid = decision === "approve" ? Boolean(reviewedValue.trim()) : Boolean(reviewerNotes.trim());

  function submit(event: FormEvent) {
    event.preventDefault();
    mutation.mutate(
      {
        reviewItemId: candidate.review_item_id,
        decision: {
          decision,
          reviewed_value: decision === "approve" ? reviewedValue.trim() : null,
          reviewer_notes: reviewerNotes.trim() || null,
        },
      },
      { onSuccess: () => onOpenChange(false) },
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="admin-review-dialog">
        <div className="admin-review-dialog-heading">
          <p className="page-eyebrow">Private field review</p>
          <DialogTitle>Review {candidate.field_name.replaceAll("_", " ")}</DialogTitle>
          <DialogDescription>
            Decide this source-backed candidate only. Saving does not publish the measure.
          </DialogDescription>
        </div>

        <div className="review-source-card">
          <div>
            <span>Official source</span>
            <strong>{candidate.source_title}</strong>
            <small>{candidate.evidence_locator} · {candidate.source_revision_id}</small>
          </div>
          <a href={candidate.official_url} target="_blank" rel="noreferrer">
            Open source <ExternalLink aria-hidden="true" />
          </a>
        </div>

        <form className="candidate-review-form" onSubmit={submit}>
          <section className="candidate-extraction">
            <span>Extracted candidate</span>
            <p>{candidate.candidate_value}</p>
            <small>{candidate.extraction_status.replaceAll("_", " ")}</small>
          </section>

          <fieldset className="review-decision-fieldset">
            <legend>Review decision</legend>
            <div role="radiogroup" aria-label="Review decision">
              <button
                type="button"
                role="radio"
                aria-checked={decision === "approve"}
                onClick={() => setDecision("approve")}
              >
                <Check aria-hidden="true" /><span><strong>Approve</strong><small>Accept a reviewed value</small></span>
              </button>
              <button
                type="button"
                role="radio"
                aria-checked={decision === "needs_revision"}
                onClick={() => setDecision("needs_revision")}
              >
                <PencilLine aria-hidden="true" /><span><strong>Needs revision</strong><small>Return for correction</small></span>
              </button>
              <button
                type="button"
                role="radio"
                aria-checked={decision === "not_applicable"}
                onClick={() => setDecision("not_applicable")}
              >
                <Ban aria-hidden="true" /><span><strong>Not applicable</strong><small>Exclude this field</small></span>
              </button>
            </div>
          </fieldset>

          {decision === "approve" && (
            <label className="admin-textarea-field">
              <span>Reviewed value</span>
              <textarea
                value={reviewedValue}
                onChange={(event) => setReviewedValue(event.target.value)}
                required
              />
              <small>Edit only when the official source supports the correction.</small>
            </label>
          )}

          <label className="admin-textarea-field">
            <span>Reviewer notes {needsNotes ? "(required)" : "(optional)"}</span>
            <textarea
              value={reviewerNotes}
              onChange={(event) => setReviewerNotes(event.target.value)}
              required={needsNotes}
              placeholder={needsNotes ? "Explain what must change or why this field does not apply." : "Record any useful verification context."}
            />
          </label>

          {mutation.isError && (
            <p className="admin-form-error" role="alert">{mutation.error.message}</p>
          )}

          <div className="admin-review-actions">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={!formIsValid || mutation.isPending}>
              {mutation.isPending ? "Saving decision…" : "Save private review"}
            </Button>
          </div>
        </form>

        {candidate.review_history.length > 0 && (
          <section className="review-history" aria-label="Review history">
            <h3><History aria-hidden="true" /> Review history</h3>
            <ol>
              {[...candidate.review_history].reverse().map((review) => (
                <li key={`${review.reviewed_at}-${review.decision}`}>
                  <strong>{decisionLabels[review.decision]}</strong>
                  <span>{review.reviewer_name} · {formatReviewDate(review.reviewed_at)}</span>
                  {review.reviewer_notes && <p>{review.reviewer_notes}</p>}
                </li>
              ))}
            </ol>
          </section>
        )}
      </DialogContent>
    </Dialog>
  );
}

export function AdminMeasureDetailPage() {
  const { measureId } = useParams({ from: "/admin/measures/$measureId" });
  const [selectedReviewItemId, setSelectedReviewItemId] = useState<string | null>(null);
  const session = useAdminSession();
  const detail = useAdminMeasure(measureId, Boolean(session.data?.authenticated));

  if (session.isPending) return <LoadingState label="Checking administrator access…" />;
  if (session.isError) return <ErrorState message={session.error.message} onRetry={() => void session.refetch()} />;
  if (!session.data.authenticated) return <AdminWorkspacePage />;
  if (detail.isPending) return <LoadingState label="Loading source-backed review candidates…" />;
  if (detail.isError) return <ErrorState message={detail.error.message} onRetry={() => void detail.refetch()} />;

  const selectedCandidate = detail.data.versions
    .flatMap((version) => version.candidates)
    .find((candidate) => candidate.review_item_id === selectedReviewItemId);

  return (
    <div className="visual-page admin-detail-page">
      <Link to="/admin" className="admin-back-link"><ArrowLeft aria-hidden="true" /> Review queue</Link>
      <header className="admin-detail-header">
        <div>
          <p className="admin-measure-id">Measure {detail.data.measure_id}</p>
          <h1>{detail.data.name}</h1>
          <p>{detail.data.description}</p>
        </div>
        <span className="private-state"><LockKeyhole aria-hidden="true" /> Private draft</span>
      </header>

      <section className="admin-membership-strip" aria-label="Program membership">
        {detail.data.memberships.map((membership) => (
          <article key={`${membership.program}-${membership.performance_year}`}>
            <span>PY{membership.performance_year}</span>
            <strong>{membership.is_program_member ? "Included" : "Not included"}</strong>
            <small>{membership.publication_state}</small>
          </article>
        ))}
      </section>

      <section className="admin-variants">
        <div className="admin-variants-heading">
          <p className="card-kicker">Versioned source review</p>
          <h2>Specification variants</h2>
          <p>Candidate values are source-derived but not verified until a reviewer decides them.</p>
        </div>
        {detail.data.versions.map((version) => (
          <article className="admin-variant-card surface-card" key={version.version_id}>
            <header>
              <div>
                <span>PY{version.performance_year}</span>
                <h3>{collectionLabels[version.collection_type] ?? version.collection_type}</h3>
                <p>{version.specification_identifier ?? "Roster membership record"}</p>
              </div>
              <div className="variant-status">
                <span>{version.publication_state}</span>
                <small>{version.candidates.length} field candidates</small>
              </div>
            </header>
            {version.candidates.length > 0 ? (
              <div className="candidate-list">
                {version.candidates.map((candidate) => (
                  <details key={candidate.review_item_id}>
                    <summary>
                      <span>{candidate.field_name.replaceAll("_", " ")}</span>
                      <code className={`candidate-status ${candidate.review_decision}`}>
                        {decisionLabels[candidate.review_decision]}
                      </code>
                    </summary>
                    <div className="candidate-body">
                      <p>{candidate.candidate_value}</p>
                      <dl>
                        <div><dt>Evidence locator</dt><dd>{candidate.evidence_locator}</dd></div>
                        <div><dt>Extraction status</dt><dd>{candidate.extraction_status}</dd></div>
                        <div><dt>Source revision</dt><dd>{candidate.source_revision_id}</dd></div>
                      </dl>
                      <a href={candidate.official_url} target="_blank" rel="noreferrer">
                        {candidate.source_title} <ExternalLink aria-hidden="true" />
                      </a>
                      <Button
                        type="button"
                        className="candidate-review-button"
                        onClick={() => setSelectedReviewItemId(candidate.review_item_id)}
                      >
                        Review candidate
                      </Button>
                    </div>
                  </details>
                ))}
              </div>
            ) : (
              <p className="variant-no-candidates">No field candidates are attached to this roster record.</p>
            )}
          </article>
        ))}
      </section>
      {selectedCandidate && (
        <CandidateReviewDialog
          key={`${selectedCandidate.review_item_id}-${selectedCandidate.reviewed_at ?? "pending"}`}
          candidate={selectedCandidate}
          measureId={measureId}
          open
          onOpenChange={(open) => {
            if (!open) setSelectedReviewItemId(null);
          }}
        />
      )}
    </div>
  );
}
