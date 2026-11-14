"""Private cross-measure review queue projections."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain import ChecklistTaskStatus, MeasureReviewStatus, ReviewDashboardStatus
from app.models import MeasureComparison, MeasureReview
from app.schemas import (
    AdminReviewChecklistProgress,
    AdminReviewDashboardItem,
    AdminReviewDashboardResponse,
    AdminReviewDashboardSummary,
)


def _dashboard_status(review: MeasureReview | None) -> ReviewDashboardStatus:
    if review is None or review.status == MeasureReviewStatus.PENDING:
        return ReviewDashboardStatus.PENDING
    if review.status in (MeasureReviewStatus.IN_REVIEW, MeasureReviewStatus.REOPENED):
        return ReviewDashboardStatus.IN_REVIEW
    if review.status == MeasureReviewStatus.COMPLETED:
        return ReviewDashboardStatus.COMPLETED
    return ReviewDashboardStatus.NEEDS_RE_REVIEW


def list_admin_review_dashboard(
    session: Session,
    *,
    status: ReviewDashboardStatus | None = None,
) -> AdminReviewDashboardResponse:
    comparisons = list(
        session.scalars(
            select(MeasureComparison)
            .options(
                selectinload(MeasureComparison.measure),
                selectinload(MeasureComparison.measure_review).selectinload(
                    MeasureReview.checklist_items
                ),
            )
            .order_by(
                MeasureComparison.from_year.desc(),
                MeasureComparison.to_year.desc(),
                MeasureComparison.measure_id,
            )
        ).unique()
    )

    counts = {item: 0 for item in ReviewDashboardStatus}
    projected: list[AdminReviewDashboardItem] = []
    for comparison in comparisons:
        review = comparison.measure_review
        dashboard_status = _dashboard_status(review)
        counts[dashboard_status] += 1
        items = review.checklist_items if review is not None else []
        open_count = sum(
            item.status == ChecklistTaskStatus.OPEN for item in items
        )
        progress = AdminReviewChecklistProgress(
            total=len(items),
            open=open_count,
            resolved=len(items) - open_count,
        )
        if status is not None and dashboard_status != status:
            continue
        projected.append(
            AdminReviewDashboardItem(
                comparison_id=comparison.id,
                measure_id=comparison.measure.measure_id,
                measure_name=comparison.measure.name,
                program=comparison.program,
                from_year=comparison.from_year,
                to_year=comparison.to_year,
                dashboard_status=dashboard_status,
                review_id=review.review_id if review is not None else None,
                review_status=review.status if review is not None else None,
                remaining_tasks=open_count,
                progress=progress,
            )
        )

    priority = {
        ReviewDashboardStatus.NEEDS_RE_REVIEW: 0,
        ReviewDashboardStatus.IN_REVIEW: 1,
        ReviewDashboardStatus.PENDING: 2,
        ReviewDashboardStatus.COMPLETED: 3,
    }
    projected.sort(
        key=lambda item: (
            priority[item.dashboard_status],
            item.measure_id,
            item.from_year,
            item.to_year,
        )
    )
    return AdminReviewDashboardResponse(
        summary=AdminReviewDashboardSummary(
            total=len(comparisons),
            pending=counts[ReviewDashboardStatus.PENDING],
            in_review=counts[ReviewDashboardStatus.IN_REVIEW],
            completed=counts[ReviewDashboardStatus.COMPLETED],
            needs_re_review=counts[ReviewDashboardStatus.NEEDS_RE_REVIEW],
        ),
        items=projected,
    )
