import { useMemo, useState, type FormEvent } from "react";
import { Check, ExternalLink, Globe2, ShieldAlert, X } from "lucide-react";

import {
  type AdminComparison,
  type AdminImpactExplanationDraft,
  useAdminImpactExplanationDrafts,
  useAdminImpactExplanationPublication,
  useAdminImpactExplanationReview,
} from "../../features/admin/api";
import type {
  ImpactExplanationOutput,
  ImpactStatement,
} from "../../features/measures/api/types";
import { formatApiDate } from "../../features/measures/api/adapters";
import { Button } from "../ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "../ui/dialog";

type Decision = "approve" | "reject";

function cloneOutput(output: ImpactExplanationOutput) {
  return structuredClone(output);
}

function statusLabel(draft: AdminImpactExplanationDraft) {
  if (draft.outdated_at) return "Needs regeneration";
  if (draft.publication_state === "published") return "Published";
  if (draft.publication_state === "withdrawn") return "Prior public version";
  if (draft.review_decision === "approve") return "Approved privately";
  if (draft.review_decision === "reject") return "Rejected";
  return "Awaiting review";
}

function StatementEditor({
  label,
  marker,
  statement,
  evidence,
  editable,
  onChange,
}: {
  label: string;
  marker?: string;
  statement: ImpactStatement;
  evidence: Map<string, AdminComparison["fields"][number]["evidence"][number]>;
  editable: boolean;
  onChange: (value: string) => void;
}) {
  return (
    <label className="impact-review-statement">
      <span>{marker ?? label}</span>
      <textarea
        aria-label={label}
        value={statement.statement}
        onChange={(event) => onChange(event.target.value)}
        readOnly={!editable}
        rows={3}
        maxLength={2000}
      />
      <small>
        {statement.citations.map((citation) => {
          const source = evidence.get(citation.evidence_id);
          return source ? (
            <a
              key={citation.evidence_id}
              href={source.official_url}
              target="_blank"
              rel="noreferrer"
            >
              {citation.evidence_id} <ExternalLink aria-hidden="true" />
            </a>
          ) : (
            <span key={citation.evidence_id}>{citation.evidence_id}</span>
          );
        })}
      </small>
    </label>
  );
}

function RoleEditor({
  title,
  eyebrow,
  sections,
  evidence,
  editable,
  onChange,
}: {
  title: string;
  eyebrow: string;
  sections: Array<{ label: string; statements: ImpactStatement[]; key: string }>;
  evidence: Map<string, AdminComparison["fields"][number]["evidence"][number]>;
  editable: boolean;
  onChange: (section: string, index: number, value: string) => void;
}) {
  return (
    <section className="impact-review-role">
      <header>
        <p>{eyebrow}</p>
        <h3>{title}</h3>
      </header>
      {sections.map((section) => (
        <div className="impact-review-section" key={section.key}>
          <p>{section.label}</p>
          {section.statements.map((statement, index) => (
            <StatementEditor
              key={`${section.key}-${index}`}
              label={`${section.label} ${index + 1}`}
              marker={`${index + 1}`.padStart(2, "0")}
              statement={statement}
              evidence={evidence}
              editable={editable}
              onChange={(value) => onChange(section.key, index, value)}
            />
          ))}
        </div>
      ))}
    </section>
  );
}

export function AdminImpactReviewDialog({
  comparison,
  onClose,
}: {
  comparison: AdminComparison | null;
  onClose: () => void;
}) {
  const drafts = useAdminImpactExplanationDrafts(
    comparison?.comparison_id ?? null,
    comparison !== null,
  );
  const review = useAdminImpactExplanationReview(comparison?.comparison_id ?? null);
  const publication = useAdminImpactExplanationPublication(comparison?.comparison_id ?? null);
  const [selectedDraftId, setSelectedDraftId] = useState<string | null>(null);
  const [editedOutputs, setEditedOutputs] = useState<Record<string, ImpactExplanationOutput>>({});
  const [decisions, setDecisions] = useState<Record<string, Decision>>({});

  const items = drafts.data?.items ?? [];
  const selectedDraft =
    items.find((item) => item.draft_id === selectedDraftId) ?? items[0] ?? null;
  const editedOutput = selectedDraft
    ? editedOutputs[selectedDraft.draft_id] ??
      cloneOutput(selectedDraft.approved_output ?? selectedDraft.output)
    : null;
  const decision = selectedDraft
    ? decisions[selectedDraft.draft_id] ??
      (selectedDraft.review_decision === "reject" ? "reject" : "approve")
    : "approve";
  const evidence = useMemo(
    () =>
      new Map(
        (comparison?.fields.flatMap((field) => field.evidence) ?? []).map((item) => [
          item.evidence_id,
          item,
        ]),
      ),
    [comparison],
  );

  function updateEditedOutput(
    update: (current: ImpactExplanationOutput) => ImpactExplanationOutput,
  ) {
    if (!selectedDraft) return;
    setEditedOutputs((current) => ({
      ...current,
      [selectedDraft.draft_id]: update(
        current[selectedDraft.draft_id] ??
          cloneOutput(selectedDraft.approved_output ?? selectedDraft.output),
      ),
    }));
  }

  function chooseDecision(value: Decision) {
    if (!selectedDraft) return;
    setDecisions((current) => ({ ...current, [selectedDraft.draft_id]: value }));
  }

  function updateRoleStatement(
    role: "data_analyst" | "aco_quality_manager",
    section: string,
    index: number,
    value: string,
  ) {
    updateEditedOutput((current) => {
      const next = cloneOutput(current);
      const roleSections = next[role] as unknown as Record<string, ImpactStatement[]>;
      roleSections[section][index].statement = value;
      return next;
    });
  }

  function submitReview(event: FormEvent) {
    event.preventDefault();
    if (!selectedDraft || !editedOutput) return;
    review.mutate({
      draftId: selectedDraft.draft_id,
      decision,
      output: decision === "approve" ? editedOutput : null,
    });
  }

  const editable = selectedDraft?.review_decision === "pending" && !selectedDraft.outdated_at;
  const actionError = review.error?.message ?? publication.error?.message;

  return (
    <Dialog open={comparison !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="admin-impact-review-dialog">
        <header className="impact-review-heading">
          <div>
            <p className="card-kicker">Private interpretation review</p>
            <DialogTitle>
              {comparison?.measure_id} · Potential impact
            </DialogTitle>
            <DialogDescription>
              Review both audience perspectives as one pair. Saving does not publish.
            </DialogDescription>
          </div>
          {items.length > 1 && (
            <label className="impact-version-select">
              <span>Version</span>
              <select
                value={selectedDraft?.draft_id ?? ""}
                onChange={(event) => setSelectedDraftId(event.target.value)}
              >
                {items.map((item, index) => (
                  <option key={item.draft_id} value={item.draft_id}>
                    {items.length - index} · {statusLabel(item)} · {formatApiDate(item.created_at)}
                  </option>
                ))}
              </select>
            </label>
          )}
        </header>

        {drafts.isPending && <div className="impact-review-empty">Loading private draft…</div>}
        {drafts.isError && (
          <div className="impact-review-empty" role="alert">
            <p>{drafts.error.message}</p>
            <Button variant="outline" onClick={() => void drafts.refetch()}>Try again</Button>
          </div>
        )}
        {!drafts.isPending && !drafts.isError && items.length === 0 && (
          <div className="impact-review-empty">
            <ShieldAlert aria-hidden="true" />
            <h3>No generated explanation is ready.</h3>
            <p>The approved comparison remains public without an AI interpretation.</p>
          </div>
        )}

        {selectedDraft && editedOutput && (
          <form onSubmit={submitReview}>
            <div className="impact-review-meta">
              <span>{statusLabel(selectedDraft)}</span>
              <span>{selectedDraft.model}</span>
              <span>{selectedDraft.cited_evidence_ids.length} evidence links</span>
            </div>
            {selectedDraft.outdated_at && (
              <p className="impact-review-warning" role="status">
                A newer source revision exists. This version is retained privately and cannot be approved or published.
              </p>
            )}

            <StatementEditor
              label="Shared factual summary"
              statement={editedOutput.plain_language_summary}
              evidence={evidence}
              editable={editable}
              onChange={(value) =>
                updateEditedOutput((current) => ({
                  ...current,
                  plain_language_summary: {
                    ...current.plain_language_summary,
                    statement: value,
                  },
                }))
              }
            />

            <div className="impact-review-pair">
              <RoleEditor
                eyebrow="Technical perspective"
                title="Data Analyst"
                sections={[
                  {
                    label: "Technical implications",
                    key: "technical_implications",
                    statements: editedOutput.data_analyst.technical_implications,
                  },
                  {
                    label: "Validation considerations",
                    key: "validation_considerations",
                    statements: editedOutput.data_analyst.validation_considerations,
                  },
                ]}
                evidence={evidence}
                editable={editable}
                onChange={(section, index, value) =>
                  updateRoleStatement("data_analyst", section, index, value)
                }
              />
              <RoleEditor
                eyebrow="Operational perspective"
                title="ACO Quality Manager"
                sections={[
                  {
                    label: "Operational implications",
                    key: "operational_implications",
                    statements: editedOutput.aco_quality_manager.operational_implications,
                  },
                  {
                    label: "Coordination considerations",
                    key: "coordination_considerations",
                    statements: editedOutput.aco_quality_manager.coordination_considerations,
                  },
                ]}
                evidence={evidence}
                editable={editable}
                onChange={(section, index, value) =>
                  updateRoleStatement("aco_quality_manager", section, index, value)
                }
              />
            </div>

            {editedOutput.uncertainty_caveats.length > 0 && (
              <section className="impact-review-caveats">
                <p>Uncertainty notes</p>
                {editedOutput.uncertainty_caveats.map((caveat, index) => (
                  <label key={index}>
                    <span>{`${index + 1}`.padStart(2, "0")}</span>
                    <textarea
                      value={caveat.statement}
                      readOnly={!editable}
                      rows={2}
                      maxLength={1000}
                      onChange={(event) =>
                        updateEditedOutput((current) => {
                          const next = cloneOutput(current);
                          next.uncertainty_caveats[index].statement = event.target.value;
                          return next;
                        })
                      }
                    />
                  </label>
                ))}
              </section>
            )}

            {editable && (
              <fieldset className="impact-review-decision">
                <legend>Pair decision</legend>
                <label>
                  <input
                    type="radio"
                    name="impact-decision"
                    checked={decision === "approve"}
                    onChange={() => chooseDecision("approve")}
                  />
                  <span><Check aria-hidden="true" /> Approve pair</span>
                </label>
                <label>
                  <input
                    type="radio"
                    name="impact-decision"
                    checked={decision === "reject"}
                    onChange={() => chooseDecision("reject")}
                  />
                  <span><X aria-hidden="true" /> Reject pair</span>
                </label>
              </fieldset>
            )}

            {actionError && <p className="admin-form-error" role="alert">{actionError}</p>}
            <footer className="impact-review-actions">
              <Button type="button" variant="outline" onClick={onClose}>Close</Button>
              {editable && (
                <Button type="submit" disabled={review.isPending}>
                  {review.isPending ? "Saving…" : decision === "approve" ? "Approve pair" : "Reject pair"}
                </Button>
              )}
              {selectedDraft.review_decision === "approve" &&
                selectedDraft.publication_state === "draft" &&
                !selectedDraft.outdated_at && (
                  <Button
                    type="button"
                    onClick={() => publication.mutate(selectedDraft.draft_id)}
                    disabled={publication.isPending || comparison?.publication_state !== "published"}
                    title={
                      comparison?.publication_state !== "published"
                        ? "Publish the approved comparison first."
                        : undefined
                    }
                  >
                    <Globe2 aria-hidden="true" />
                    {publication.isPending ? "Publishing…" : "Publish explanation"}
                  </Button>
                )}
            </footer>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
