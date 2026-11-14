import {
  BadgeCheck,
  CheckCircle2,
  CircleDotDashed,
  ListPlus,
  MessageSquareText,
  PencilLine,
  RefreshCw,
  Sparkles,
  X,
} from "lucide-react";

import {
  type AdminReviewEventType,
  useAdminMeasureReviewActivity,
} from "../../features/admin/api";
import { Button } from "../ui/button";

const statusLabels = {
  pending: "Pending",
  in_review: "In review",
  completed: "Completed",
  reopened: "Reopened",
  needs_re_review: "Needs re-review",
} as const;

const dateFormatter = new Intl.DateTimeFormat("en-US", {
  dateStyle: "medium",
  timeStyle: "short",
});

function eventIcon(eventType: AdminReviewEventType) {
  if (eventType === "review_created") return <CircleDotDashed aria-hidden="true" />;
  if (eventType === "proposal_created") return <Sparkles aria-hidden="true" />;
  if (eventType === "proposal_dismissed") return <X aria-hidden="true" />;
  if (eventType === "proposal_accepted" || eventType === "task_added") {
    return <ListPlus aria-hidden="true" />;
  }
  if (eventType === "task_edited") return <PencilLine aria-hidden="true" />;
  if (eventType === "task_status_changed") return <CheckCircle2 aria-hidden="true" />;
  if (eventType === "note_added") return <MessageSquareText aria-hidden="true" />;
  if (eventType === "signed_off") return <BadgeCheck aria-hidden="true" />;
  return <RefreshCw aria-hidden="true" />;
}

export function AdminReviewActivityTimeline({ measureId }: { measureId: string }) {
  const activity = useAdminMeasureReviewActivity(measureId, true);
  const eventCount = activity.data?.reviews.reduce(
    (total, review) => total + review.events.length,
    0,
  ) ?? 0;

  return (
    <section className="admin-review-activity" aria-labelledby="review-activity-title">
      <header>
        <div>
          <p className="card-kicker">Private audit trail</p>
          <h2 id="review-activity-title">Review activity</h2>
          <p>Checklist decisions, notes and sign-offs retained in recorded order.</p>
        </div>
        {eventCount > 0 && <span>{eventCount} recorded events</span>}
      </header>

      {activity.isPending && (
        <div className="admin-review-activity-empty">Loading review activity…</div>
      )}
      {activity.isError && (
        <div className="admin-review-activity-empty" role="alert">
          <p>{activity.error.message}</p>
          <Button variant="outline" onClick={() => void activity.refetch()}>Try again</Button>
        </div>
      )}
      {!activity.isPending && !activity.isError && activity.data?.reviews.length === 0 && (
        <div className="admin-review-activity-empty">
          No checklist review activity has been recorded for this measure.
        </div>
      )}

      <div className="admin-review-activity-groups">
        {activity.data?.reviews.map((review) => (
          <article className="admin-review-activity-group surface-card" key={review.review_id}>
            <header>
              <div>
                <strong>PY{review.from_year} → PY{review.to_year}</strong>
                <small>{review.program}</small>
              </div>
              <span className={`status-${review.review_status}`}>
                {statusLabels[review.review_status]}
              </span>
            </header>
            <ol>
              {review.events.map((event) => (
                <li className={`event-${event.event_type}`} key={event.event_id}>
                  <span className="admin-review-activity-marker">
                    {eventIcon(event.event_type)}
                  </span>
                  <div>
                    <header>
                      <strong>{event.title}</strong>
                      <time dateTime={event.occurred_at}>
                        {dateFormatter.format(new Date(event.occurred_at))}
                      </time>
                    </header>
                    <p>{event.detail}</p>
                    {event.note && <blockquote>{event.note}</blockquote>}
                    <small>{event.actor} · Event {event.sequence}</small>
                  </div>
                </li>
              ))}
            </ol>
          </article>
        ))}
      </div>
    </section>
  );
}
