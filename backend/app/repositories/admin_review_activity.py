"""Private, presentation-ready activity timeline for measure reviews."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain import ReviewEventType
from app.models import (
    Measure,
    MeasureComparison,
    MeasureReview,
    ReviewChecklistItem,
    ReviewEvent,
    ReviewSignOff,
    ReviewTaskProposal,
)
from app.schemas import (
    AdminMeasureReviewActivityResponse,
    AdminReviewActivityEventResponse,
    AdminReviewActivityReviewResponse,
)

EVENT_TITLES = {
    ReviewEventType.REVIEW_CREATED: "Review started",
    ReviewEventType.PROPOSAL_CREATED: "Suggested action generated",
    ReviewEventType.PROPOSAL_ACCEPTED: "Suggestion accepted",
    ReviewEventType.PROPOSAL_DISMISSED: "Suggestion dismissed",
    ReviewEventType.TASK_ADDED: "Task added",
    ReviewEventType.TASK_EDITED: "Task updated",
    ReviewEventType.TASK_STATUS_CHANGED: "Task status changed",
    ReviewEventType.NOTE_ADDED: "Review note added",
    ReviewEventType.SIGNED_OFF: "Review signed off",
    ReviewEventType.REOPENED: "Review reopened",
    ReviewEventType.NEEDS_RE_REVIEW: "Needs re-review",
}

FIELD_LABELS = {
    "role": "role",
    "title": "title",
    "description": "details",
    "notes": "private notes",
}

STATUS_LABELS = {
    "open": "Open",
    "completed": "Completed",
    "not_applicable": "Not applicable",
}

ROLE_LABELS = {
    "data_analyst": "Data Analyst",
    "aco_quality_manager": "ACO Quality Manager",
    "both": "Both roles",
}


def _string(payload: dict[str, object], key: str) -> str | None:
    value = payload.get(key)
    return value if isinstance(value, str) else None


def _strings(payload: dict[str, object], key: str) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _subject_title(
    event: ReviewEvent,
    tasks: dict[str, ReviewChecklistItem],
    proposals: dict[str, ReviewTaskProposal],
) -> str | None:
    snapshot = _string(event.payload, "task_title")
    if snapshot:
        return snapshot
    if event.subject_type == "checklist_item" and event.subject_id in tasks:
        return tasks[event.subject_id].title
    if event.subject_type == "task_proposal" and event.subject_id in proposals:
        return proposals[event.subject_id].title
    return None


def _quoted(value: str | None) -> str:
    return f'“{value}”' if value else "The review item"


def _event_detail(
    event: ReviewEvent,
    *,
    comparison: MeasureComparison,
    tasks: dict[str, ReviewChecklistItem],
    proposals: dict[str, ReviewTaskProposal],
    signoffs: dict[str, ReviewSignOff],
) -> str:
    subject = _subject_title(event, tasks, proposals)
    payload = event.payload
    if event.event_type == ReviewEventType.REVIEW_CREATED:
        return f"Private review opened for PY{comparison.from_year} → PY{comparison.to_year}."
    if event.event_type == ReviewEventType.PROPOSAL_CREATED:
        role = ROLE_LABELS.get(_string(payload, "role") or "", "Shared")
        return f"{_quoted(subject)} was generated for {role}."
    if event.event_type == ReviewEventType.PROPOSAL_ACCEPTED:
        return f"{_quoted(subject)} was accepted into the shared checklist."
    if event.event_type == ReviewEventType.PROPOSAL_DISMISSED:
        return f"{_quoted(subject)} was dismissed without changing the checklist."
    if event.event_type == ReviewEventType.TASK_ADDED:
        role = ROLE_LABELS.get(_string(payload, "role") or "", "the shared review")
        return f"{_quoted(subject)} was added for {role}."
    if event.event_type == ReviewEventType.TASK_EDITED:
        labels = [
            FIELD_LABELS.get(field, field.replace("_", " "))
            for field in _strings(payload, "changed_fields")
        ]
        changed = ", ".join(labels) if labels else "Task details"
        return f"{changed.capitalize()} updated for {_quoted(subject)}."
    if event.event_type == ReviewEventType.TASK_STATUS_CHANGED:
        from_status = STATUS_LABELS.get(_string(payload, "from_status") or "", "Unknown")
        to_status = STATUS_LABELS.get(_string(payload, "to_status") or "", "Unknown")
        return f"{_quoted(subject)} moved from {from_status} to {to_status}."
    if event.event_type == ReviewEventType.NOTE_ADDED:
        return "A private note was added to this review."
    if event.event_type == ReviewEventType.SIGNED_OFF:
        signoff = signoffs.get(event.subject_id or "")
        accepted = signoff.accepted_task_count if signoff else payload.get("accepted_task_count", 0)
        resolved = signoff.resolved_task_count if signoff else payload.get("resolved_task_count", 0)
        return f"{resolved} of {accepted} accepted tasks were resolved at sign-off."
    if event.event_type == ReviewEventType.REOPENED:
        return "A completed review was reopened for another review pass."
    if event.event_type == ReviewEventType.NEEDS_RE_REVIEW:
        return "A newer official source revision requires another review pass."
    return "Private review activity recorded."


def get_measure_review_activity(
    session: Session,
    *,
    measure_id: str,
) -> AdminMeasureReviewActivityResponse | None:
    if session.scalar(select(Measure.id).where(Measure.measure_id == measure_id)) is None:
        return None

    reviews = list(
        session.scalars(
            select(MeasureReview)
            .join(MeasureReview.comparison)
            .join(MeasureComparison.measure)
            .where(Measure.measure_id == measure_id)
            .options(
                selectinload(MeasureReview.comparison),
                selectinload(MeasureReview.events),
                selectinload(MeasureReview.checklist_items),
                selectinload(MeasureReview.task_proposals),
                selectinload(MeasureReview.signoffs),
            )
            .order_by(MeasureReview.created_at.desc(), MeasureReview.id.desc())
        ).unique()
    )

    review_responses = []
    for review in reviews:
        tasks = {item.checklist_item_id: item for item in review.checklist_items}
        proposals = {item.proposal_id: item for item in review.task_proposals}
        signoffs = {item.signoff_id: item for item in review.signoffs}
        events = [
            AdminReviewActivityEventResponse(
                event_id=event.event_id,
                sequence=event.sequence,
                event_type=event.event_type,
                title=EVENT_TITLES[event.event_type],
                detail=_event_detail(
                    event,
                    comparison=review.comparison,
                    tasks=tasks,
                    proposals=proposals,
                    signoffs=signoffs,
                ),
                actor=event.actor,
                occurred_at=event.occurred_at,
                note=(
                    signoffs[event.subject_id].note
                    if event.event_type == ReviewEventType.SIGNED_OFF
                    and event.subject_id in signoffs
                    else event.note
                ),
            )
            for event in sorted(review.events, key=lambda item: item.sequence, reverse=True)
        ]
        comparison = review.comparison
        review_responses.append(
            AdminReviewActivityReviewResponse(
                review_id=review.review_id,
                comparison_id=comparison.id,
                review_status=review.status,
                program=comparison.program,
                collection_type=comparison.collection_type,
                from_year=comparison.from_year,
                to_year=comparison.to_year,
                events=events,
            )
        )

    return AdminMeasureReviewActivityResponse(
        measure_id=measure_id,
        reviews=review_responses,
    )
