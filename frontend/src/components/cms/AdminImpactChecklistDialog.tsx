import { useMemo, useState, type FormEvent } from "react";
import {
  Ban,
  Check,
  Circle,
  ClipboardCheck,
  ExternalLink,
  Pencil,
  Plus,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";

import {
  type AdminChecklistStatus,
  type AdminComparison,
  type AdminReviewChecklistItem,
  type AdminReviewChecklistItemInput,
  type AdminReviewRole,
  useAdminChecklistItemCreate,
  useAdminChecklistItemUpdate,
  useAdminReviewChecklist,
  useAdminReviewLifecycle,
  useAdminTaskProposalDecision,
  useAdminTaskProposalGeneration,
} from "../../features/admin/api";
import { formatApiDate } from "../../features/measures/api/adapters";
import { Button } from "../ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "../ui/dialog";

type RoleFilter = "all" | Exclude<AdminReviewRole, "both">;

const emptyItem: AdminReviewChecklistItemInput = {
  role: "data_analyst",
  title: "",
  description: null,
  notes: null,
};

function roleLabel(role: AdminReviewRole) {
  if (role === "data_analyst") return "Data Analyst";
  if (role === "aco_quality_manager") return "ACO Quality Manager";
  return "Both roles";
}

function statusLabel(status: AdminChecklistStatus) {
  if (status === "not_applicable") return "Not applicable";
  return status === "completed" ? "Completed" : "Open";
}

function matchesRole(role: AdminReviewRole, filter: RoleFilter) {
  return filter === "all" || role === filter || role === "both";
}

function TaskFields({
  value,
  onChange,
  titlePrefix,
  disabled = false,
}: {
  value: AdminReviewChecklistItemInput;
  onChange: (value: AdminReviewChecklistItemInput) => void;
  titlePrefix: string;
  disabled?: boolean;
}) {
  return (
    <div className="impact-checklist-fields">
      <label>
        <span>Role</span>
        <select
          aria-label={`${titlePrefix} role`}
          value={value.role}
          disabled={disabled}
          onChange={(event) =>
            onChange({ ...value, role: event.target.value as AdminReviewRole })
          }
        >
          <option value="data_analyst">Data Analyst</option>
          <option value="aco_quality_manager">ACO Quality Manager</option>
          <option value="both">Both roles</option>
        </select>
      </label>
      <label className="wide">
        <span>Task</span>
        <input
          aria-label={`${titlePrefix} title`}
          value={value.title}
          maxLength={500}
          required
          disabled={disabled}
          onChange={(event) => onChange({ ...value, title: event.target.value })}
        />
      </label>
      <label className="wide">
        <span>Details</span>
        <textarea
          aria-label={`${titlePrefix} details`}
          value={value.description ?? ""}
          maxLength={4000}
          rows={2}
          disabled={disabled}
          onChange={(event) =>
            onChange({ ...value, description: event.target.value || null })
          }
        />
      </label>
      <label className="wide">
        <span>Private notes</span>
        <textarea
          aria-label={`${titlePrefix} notes`}
          value={value.notes ?? ""}
          maxLength={4000}
          rows={2}
          disabled={disabled}
          onChange={(event) => onChange({ ...value, notes: event.target.value || null })}
        />
      </label>
    </div>
  );
}

function ChecklistItem({
  item,
  busy,
  onUpdate,
}: {
  item: AdminReviewChecklistItem;
  busy: boolean;
  onUpdate: (
    checklistItemId: string,
    update: Partial<AdminReviewChecklistItemInput> & { status?: AdminChecklistStatus },
    onSuccess?: () => void,
  ) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<AdminReviewChecklistItemInput>({
    role: item.role,
    title: item.title,
    description: item.description,
    notes: item.notes,
  });

  function save(event: FormEvent) {
    event.preventDefault();
    onUpdate(item.checklist_item_id, draft, () => setEditing(false));
  }

  function startEditing() {
    if (busy) return;
    setDraft({
      role: item.role,
      title: item.title,
      description: item.description,
      notes: item.notes,
    });
    setEditing(true);
  }

  return (
    <article className={`impact-checklist-item status-${item.status}`}>
      <header>
        <div>
          <span>{roleLabel(item.role)}</span>
          <h4>{item.title}</h4>
        </div>
        <span className="impact-checklist-status">{statusLabel(item.status)}</span>
      </header>
      {!editing && item.description && <p>{item.description}</p>}
      {!editing && item.notes && <small>{item.notes}</small>}

      {editing ? (
        <form onSubmit={save}>
          <TaskFields
            value={draft}
            onChange={setDraft}
            titlePrefix={`Edit ${item.title}`}
            disabled={busy}
          />
          <footer>
            <Button type="button" variant="ghost" onClick={() => setEditing(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={busy || !draft.title.trim()}>Save task</Button>
          </footer>
        </form>
      ) : (
        <footer>
          <Button type="button" variant="ghost" disabled={busy} onClick={startEditing}>
            <Pencil aria-hidden="true" /> Edit
          </Button>
          <div className="impact-checklist-state-actions" aria-label={`Set status for ${item.title}`}>
            <Button
              type="button"
              variant="ghost"
              disabled={busy || item.status === "open"}
              onClick={() => onUpdate(item.checklist_item_id, { status: "open" })}
            >
              <Circle aria-hidden="true" /> Open
            </Button>
            <Button
              type="button"
              variant="ghost"
              disabled={busy || item.status === "completed"}
              onClick={() => onUpdate(item.checklist_item_id, { status: "completed" })}
            >
              <Check aria-hidden="true" /> Complete
            </Button>
            <Button
              type="button"
              variant="ghost"
              disabled={busy || item.status === "not_applicable"}
              onClick={() => onUpdate(item.checklist_item_id, { status: "not_applicable" })}
            >
              <Ban aria-hidden="true" /> N/A
            </Button>
          </div>
        </footer>
      )}
    </article>
  );
}

export function AdminImpactChecklistDialog({
  comparison,
  onClose,
}: {
  comparison: AdminComparison | null;
  onClose: () => void;
}) {
  const comparisonId = comparison?.comparison_id ?? null;
  const checklist = useAdminReviewChecklist(comparisonId, comparison !== null);
  const generation = useAdminTaskProposalGeneration(comparisonId);
  const proposalDecision = useAdminTaskProposalDecision(comparisonId);
  const createItem = useAdminChecklistItemCreate(comparisonId);
  const updateItem = useAdminChecklistItemUpdate(comparisonId);
  const lifecycle = useAdminReviewLifecycle(comparisonId);
  const [filter, setFilter] = useState<RoleFilter>("all");
  const [adding, setAdding] = useState(false);
  const [newItem, setNewItem] = useState<AdminReviewChecklistItemInput>(emptyItem);
  const [signoffNote, setSignoffNote] = useState("");

  const data = checklist.data;
  const proposals = useMemo(
    () =>
      (data?.proposals ?? []).filter(
        (item) => item.status === "pending" && matchesRole(item.role, filter),
      ),
    [data?.proposals, filter],
  );
  const items = useMemo(
    () => (data?.items ?? []).filter((item) => matchesRole(item.role, filter)),
    [data?.items, filter],
  );
  const reviewCompleted = data?.review_status === "completed";
  const latestSignoff = data?.signoffs.at(-1) ?? null;
  const actionError =
    generation.error?.message ??
    proposalDecision.error?.message ??
    createItem.error?.message ??
    updateItem.error?.message ??
    lifecycle.error?.message;

  function submitNewItem(event: FormEvent) {
    event.preventDefault();
    createItem.mutate(newItem, {
      onSuccess: () => {
        setNewItem(emptyItem);
        setAdding(false);
      },
    });
  }

  function updateReviewLifecycle(action: "sign-off" | "reopen") {
    if (!data?.review_id) return;
    lifecycle.mutate(
      {
        reviewId: data.review_id,
        action,
        note: signoffNote.trim() || null,
      },
      {
        onSuccess: () => {
          setAdding(false);
          setSignoffNote("");
        },
      },
    );
  }

  return (
    <Dialog open={comparison !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="admin-impact-checklist-dialog">
        <header className="impact-checklist-heading">
          <div>
            <p className="card-kicker">Private follow-up desk</p>
            <DialogTitle>{comparison?.measure_id} · Impact checklist</DialogTitle>
            <DialogDescription>
              Accept useful suggestions, assign follow-up work, and record resolution.
            </DialogDescription>
          </div>
          <div className="impact-checklist-progress" aria-label="Checklist progress">
            <strong>{data?.progress.resolved ?? 0}/{data?.progress.total ?? 0}</strong>
            <span>resolved</span>
          </div>
        </header>

        {checklist.isPending && <div className="impact-review-empty">Loading checklist…</div>}
        {checklist.isError && (
          <div className="impact-review-empty" role="alert">
            <p>{checklist.error.message}</p>
            <Button variant="outline" onClick={() => void checklist.refetch()}>Try again</Button>
          </div>
        )}

        {data && (
          <div className="impact-checklist-body">
            <nav className="impact-checklist-filters" aria-label="Filter checklist by role">
              {([
                ["all", "All"],
                ["data_analyst", "Data Analyst"],
                ["aco_quality_manager", "ACO Quality Manager"],
              ] as const).map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  aria-pressed={filter === value}
                  onClick={() => setFilter(value)}
                >
                  {label}
                </button>
              ))}
            </nav>

            {actionError && <p className="admin-form-error" role="alert">{actionError}</p>}

            <div className="impact-checklist-columns">
              <section className="impact-suggestion-column" aria-labelledby="suggested-tasks-title">
                <header>
                  <div>
                    <p className="card-kicker">Optional AI output</p>
                    <h3 id="suggested-tasks-title">Suggested actions</h3>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    disabled={
                      reviewCompleted ||
                      !data.eligible_impact_explanation_draft_id ||
                      generation.isPending
                    }
                    title={
                      data.eligible_impact_explanation_draft_id
                        ? undefined
                        : "Approve a current impact explanation first."
                    }
                    onClick={() =>
                      data.eligible_impact_explanation_draft_id &&
                      generation.mutate(data.eligible_impact_explanation_draft_id)
                    }
                  >
                    <Sparkles aria-hidden="true" />
                    {generation.isPending ? "Generating…" : "Generate"}
                  </Button>
                </header>
                {proposals.length === 0 ? (
                  <div className="impact-checklist-blank">
                    <Sparkles aria-hidden="true" />
                    <p>No pending suggestions for this role.</p>
                  </div>
                ) : (
                  <div className="impact-suggestion-list">
                    {proposals.map((proposal) => (
                      <article key={proposal.proposal_id}>
                        <span>{roleLabel(proposal.role)}</span>
                        <h4>{proposal.title}</h4>
                        {proposal.description && <p>{proposal.description}</p>}
                        <small>
                          {proposal.evidence.map((evidence) => (
                            <a
                              key={evidence.evidence_id}
                              href={evidence.official_url}
                              target="_blank"
                              rel="noreferrer"
                            >
                              Evidence <ExternalLink aria-hidden="true" />
                            </a>
                          ))}
                        </small>
                        <footer>
                          <Button
                            type="button"
                            variant="ghost"
                            disabled={reviewCompleted || proposalDecision.isPending}
                            onClick={() =>
                              proposalDecision.mutate({
                                proposalId: proposal.proposal_id,
                                decision: "dismiss",
                              })
                            }
                          >
                            <X aria-hidden="true" /> Dismiss
                          </Button>
                          <Button
                            type="button"
                            disabled={reviewCompleted || proposalDecision.isPending}
                            onClick={() =>
                              proposalDecision.mutate({
                                proposalId: proposal.proposal_id,
                                decision: "accept",
                              })
                            }
                          >
                            <Plus aria-hidden="true" /> Accept
                          </Button>
                        </footer>
                      </article>
                    ))}
                  </div>
                )}
              </section>

              <section className="impact-active-column" aria-labelledby="active-tasks-title">
                <header>
                  <div>
                    <p className="card-kicker">Shared human checklist</p>
                    <h3 id="active-tasks-title">Accepted tasks</h3>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    disabled={reviewCompleted}
                    onClick={() => setAdding(true)}
                  >
                    <Plus aria-hidden="true" /> Add task
                  </Button>
                </header>

                {adding && (
                  <form className="impact-checklist-new" onSubmit={submitNewItem}>
                    <TaskFields
                      value={newItem}
                      onChange={setNewItem}
                      titlePrefix="New task"
                      disabled={reviewCompleted}
                    />
                    <footer>
                      <Button type="button" variant="ghost" onClick={() => setAdding(false)}>
                        Cancel
                      </Button>
                      <Button type="submit" disabled={createItem.isPending || !newItem.title.trim()}>
                        {createItem.isPending ? "Adding…" : "Add to checklist"}
                      </Button>
                    </footer>
                  </form>
                )}

                {items.length === 0 ? (
                  <div className="impact-checklist-blank">
                    <ClipboardCheck aria-hidden="true" />
                    <p>No accepted tasks for this role.</p>
                  </div>
                ) : (
                  <div className="impact-checklist-list">
                    {items.map((item) => (
                      <ChecklistItem
                        key={item.checklist_item_id}
                        item={item}
                        busy={reviewCompleted || updateItem.isPending}
                        onUpdate={(checklistItemId, update, onSuccess) =>
                          updateItem.mutate({ checklistItemId, update }, { onSuccess })
                        }
                      />
                    ))}
                  </div>
                )}
              </section>
            </div>

            <section
              className={`impact-review-completion${reviewCompleted ? " is-complete" : ""}`}
              aria-labelledby="review-completion-title"
            >
              <div className="impact-review-completion-copy">
                <div className="impact-review-completion-title">
                  <ShieldCheck aria-hidden="true" />
                  <div>
                    <p className="card-kicker">Review completion</p>
                    <h3 id="review-completion-title">
                      {reviewCompleted ? "Signed off" : "Ready for sign-off?"}
                    </h3>
                  </div>
                </div>
                {reviewCompleted && latestSignoff ? (
                  <p>
                    Sign-off {latestSignoff.sequence} · {latestSignoff.signed_by} ·{" "}
                    {formatApiDate(latestSignoff.signed_at)}
                    {latestSignoff.note ? ` · ${latestSignoff.note}` : ""}
                  </p>
                ) : (
                  <p>
                    {data.signoff_blocker ??
                      "Every accepted task is resolved. Confirm this review to complete it."}
                  </p>
                )}
              </div>

              <div className="impact-review-completion-actions">
                {!reviewCompleted && (
                  <label>
                    <span>Sign-off note (optional)</span>
                    <input
                      value={signoffNote}
                      maxLength={4000}
                      disabled={!data.review_id || lifecycle.isPending}
                      onChange={(event) => setSignoffNote(event.target.value)}
                    />
                  </label>
                )}
                {reviewCompleted ? (
                  <Button
                    type="button"
                    variant="outline"
                    disabled={!data.review_id || lifecycle.isPending}
                    onClick={() => updateReviewLifecycle("reopen")}
                  >
                    <RotateCcw aria-hidden="true" />
                    {lifecycle.isPending ? "Reopening…" : "Reopen review"}
                  </Button>
                ) : (
                  <Button
                    type="button"
                    disabled={!data.can_sign_off || lifecycle.isPending}
                    onClick={() => updateReviewLifecycle("sign-off")}
                  >
                    <ShieldCheck aria-hidden="true" />
                    {lifecycle.isPending ? "Signing off…" : "Confirm sign-off"}
                  </Button>
                )}
              </div>
            </section>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
