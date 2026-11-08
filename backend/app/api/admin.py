import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, Request, Response
from sqlalchemy.orm import Session

from app.auth import (
    SESSION_COOKIE_NAME,
    AdminIdentity,
    admin_auth_is_configured,
    create_admin_session,
    read_admin_session,
    require_admin,
    verify_admin_password,
)
from app.config import Settings, get_settings
from app.database import get_db
from app.domain import (
    CandidateReviewDecision,
    CollectionType,
    ComparisonReviewDecision,
    ImpactExplanationReviewDecision,
    PublicationState,
)
from app.repositories.admin_comparisons import (
    admin_comparison_response,
    get_admin_comparison,
    list_admin_comparisons,
    prepare_roster_comparisons,
)
from app.repositories.admin_impact_explanations import (
    get_impact_explanation_draft,
    impact_draft_response,
    list_impact_explanation_drafts,
)
from app.repositories.admin_reviews import (
    candidate_response,
    get_private_candidate,
    get_private_measure,
    list_private_measures,
    review_summary,
)
from app.schemas import (
    AdminCandidateDecisionRequest,
    AdminComparisonDecisionRequest,
    AdminComparisonGenerationRequest,
    AdminComparisonGenerationResponse,
    AdminComparisonPage,
    AdminComparisonResponse,
    AdminFieldCandidateResponse,
    AdminImpactExplanationDraftPage,
    AdminImpactExplanationDraftResponse,
    AdminImpactExplanationReviewRequest,
    AdminLoginRequest,
    AdminMeasureDetail,
    AdminMeasurePage,
    AdminReviewSummary,
    AdminSessionResponse,
    ApiError,
)
from app.services.ai_impact_explanation import (
    ImpactGenerationError,
    ImpactProviderError,
    generate_impact_explanation,
)
from app.services.ai_impact_explanation import (
    provider_from_settings as impact_provider_from_settings,
)
from app.services.comparison_publication import (
    ComparisonPublicationError,
    publish_approved_comparison,
    record_comparison_review,
)
from app.services.impact_explanation_review import (
    ImpactExplanationReviewError,
    publish_approved_impact_explanation,
    record_impact_explanation_review,
)
from app.services.publication import FieldPublicationError, publish_approved_field
from app.services.reviews import record_candidate_review

router = APIRouter(prefix="/api/admin", tags=["Admin review"])
DatabaseSession = Annotated[Session, Depends(get_db)]
ApplicationSettings = Annotated[Settings, Depends(get_settings)]
AuthenticatedAdmin = Annotated[AdminIdentity, Depends(require_admin)]
auth_responses = {
    401: {"model": ApiError, "description": "Administrator authentication is required."}
}


def require_admin_action_header(
    action: Annotated[str, Header(alias="X-CMSQI-Admin-Action")],
) -> None:
    if not hmac.compare_digest(action, "review-decision"):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "invalid_admin_action_header",
                "message": "The required administrator action header is invalid.",
                "details": [],
            },
        )


AdminActionHeader = Annotated[None, Depends(require_admin_action_header)]


def require_field_publication_header(
    action: Annotated[str, Header(alias="X-CMSQI-Admin-Action")],
) -> None:
    if not hmac.compare_digest(action, "publish-field"):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "invalid_admin_action_header",
                "message": "The required administrator action header is invalid.",
                "details": [],
            },
        )


FieldPublicationHeader = Annotated[None, Depends(require_field_publication_header)]


def _require_comparison_action(expected: str, action: str) -> None:
    if not hmac.compare_digest(action, expected):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "invalid_admin_action_header",
                "message": "The required administrator action header is invalid.",
                "details": [],
            },
        )


def require_comparison_prepare_header(
    action: Annotated[str, Header(alias="X-CMSQI-Admin-Action")],
) -> None:
    _require_comparison_action("prepare-comparisons", action)


def require_comparison_review_header(
    action: Annotated[str, Header(alias="X-CMSQI-Admin-Action")],
) -> None:
    _require_comparison_action("review-comparison", action)


def require_comparison_publish_header(
    action: Annotated[str, Header(alias="X-CMSQI-Admin-Action")],
) -> None:
    _require_comparison_action("publish-comparison", action)


def require_impact_generation_header(
    action: Annotated[str, Header(alias="X-CMSQI-Admin-Action")],
) -> None:
    _require_comparison_action("generate-impact-explanation", action)


def require_impact_review_header(
    action: Annotated[str, Header(alias="X-CMSQI-Admin-Action")],
) -> None:
    _require_comparison_action("review-impact-explanation", action)


def require_impact_publish_header(
    action: Annotated[str, Header(alias="X-CMSQI-Admin-Action")],
) -> None:
    _require_comparison_action("publish-impact-explanation", action)


ComparisonPrepareHeader = Annotated[None, Depends(require_comparison_prepare_header)]
ComparisonReviewHeader = Annotated[None, Depends(require_comparison_review_header)]
ComparisonPublishHeader = Annotated[None, Depends(require_comparison_publish_header)]
ImpactGenerationHeader = Annotated[None, Depends(require_impact_generation_header)]
ImpactReviewHeader = Annotated[None, Depends(require_impact_review_header)]
ImpactPublishHeader = Annotated[None, Depends(require_impact_publish_header)]


def _session_response(request: Request, settings: Settings) -> AdminSessionResponse:
    identity = read_admin_session(request.cookies.get(SESSION_COOKIE_NAME), settings)
    return AdminSessionResponse(
        configured=admin_auth_is_configured(settings),
        authenticated=identity is not None,
        username=identity.username if identity else None,
    )


@router.get(
    "/session",
    response_model=AdminSessionResponse,
    operation_id="getAdminSession",
)
def admin_session(request: Request, settings: ApplicationSettings) -> AdminSessionResponse:
    return _session_response(request, settings)


@router.post(
    "/session",
    response_model=AdminSessionResponse,
    operation_id="createAdminSession",
    responses={401: auth_responses[401], 503: {"model": ApiError}},
)
def login(
    credentials: AdminLoginRequest,
    response: Response,
    settings: ApplicationSettings,
) -> AdminSessionResponse:
    if not admin_auth_is_configured(settings):
        raise HTTPException(
            status_code=503,
            detail={
                "code": "admin_authentication_not_configured",
                "message": "Administrator authentication has not been configured.",
                "details": [],
            },
        )
    username_matches = hmac.compare_digest(credentials.username, settings.admin_username)
    password_matches = verify_admin_password(
        credentials.password, settings.admin_password_hash
    )
    if not username_matches or not password_matches:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "invalid_admin_credentials",
                "message": "The administrator credentials were not accepted.",
                "details": [],
            },
        )
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=create_admin_session(settings.admin_username, settings),
        max_age=settings.admin_session_ttl_seconds,
        httponly=True,
        secure=settings.admin_session_secure,
        samesite="lax",
        path="/api/admin",
    )
    return AdminSessionResponse(
        configured=True, authenticated=True, username=settings.admin_username
    )


@router.delete(
    "/session",
    response_model=AdminSessionResponse,
    operation_id="deleteAdminSession",
)
def logout(response: Response, settings: ApplicationSettings) -> AdminSessionResponse:
    response.delete_cookie(SESSION_COOKIE_NAME, path="/api/admin")
    return AdminSessionResponse(
        configured=admin_auth_is_configured(settings),
        authenticated=False,
        username=None,
    )


@router.get(
    "/review-summary",
    response_model=AdminReviewSummary,
    operation_id="getAdminReviewSummary",
    responses=auth_responses,
)
def admin_review_summary(
    session: DatabaseSession, _admin: AuthenticatedAdmin
) -> AdminReviewSummary:
    return review_summary(session)


@router.get(
    "/measures",
    response_model=AdminMeasurePage,
    operation_id="listAdminMeasures",
    responses=auth_responses,
)
def admin_measures(
    session: DatabaseSession,
    _admin: AuthenticatedAdmin,
    q: Annotated[str | None, Query(max_length=200)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> AdminMeasurePage:
    return list_private_measures(session, q=q, page=page, page_size=page_size)


@router.get(
    "/measures/{measure_id}",
    response_model=AdminMeasureDetail,
    operation_id="getAdminMeasure",
    responses={
        **auth_responses,
        404: {"model": ApiError, "description": "The review measure was not found."},
    },
)
def admin_measure_detail(
    session: DatabaseSession,
    _admin: AuthenticatedAdmin,
    measure_id: Annotated[str, Path(min_length=1)],
) -> AdminMeasureDetail:
    result = get_private_measure(session, measure_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "not_found",
                "message": f"Review measure '{measure_id}' was not found.",
                "details": [],
            },
        )
    return result


@router.get(
    "/comparisons",
    response_model=AdminComparisonPage,
    operation_id="listAdminComparisons",
    responses=auth_responses,
)
def admin_comparisons(
    session: DatabaseSession,
    _admin: AuthenticatedAdmin,
    from_year: Annotated[int, Query(ge=2000, le=2100)] = 2025,
    to_year: Annotated[int, Query(ge=2000, le=2100)] = 2026,
    collection_type: CollectionType = CollectionType.PROGRAM_ROSTER,
) -> AdminComparisonPage:
    if from_year == to_year:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "invalid_year_pair",
                "message": "Comparison years must be different.",
                "details": [],
            },
        )
    return list_admin_comparisons(
        session,
        from_year=from_year,
        to_year=to_year,
        collection_type=collection_type,
    )


@router.get(
    "/comparisons/{comparison_id}/impact-explanations",
    response_model=AdminImpactExplanationDraftPage,
    operation_id="listAdminImpactExplanationDrafts",
    responses={
        **auth_responses,
        404: {"model": ApiError, "description": "The comparison was not found."},
    },
)
def admin_impact_explanation_drafts(
    session: DatabaseSession,
    _admin: AuthenticatedAdmin,
    comparison_id: Annotated[int, Path(ge=1)],
) -> AdminImpactExplanationDraftPage:
    if get_admin_comparison(session, comparison_id) is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "not_found",
                "message": f"Comparison '{comparison_id}' was not found.",
                "details": [],
            },
        )
    return list_impact_explanation_drafts(session, comparison_id=comparison_id)


@router.post(
    "/comparisons/{comparison_id}/impact-explanations/generate",
    response_model=AdminImpactExplanationDraftResponse,
    operation_id="generateAdminImpactExplanationDraft",
    responses={
        **auth_responses,
        403: {"model": ApiError, "description": "The admin action header is invalid."},
        404: {"model": ApiError, "description": "The comparison was not found."},
        409: {"model": ApiError, "description": "The comparison is not eligible."},
        502: {"model": ApiError, "description": "The provider request failed."},
        503: {"model": ApiError, "description": "Impact generation is not configured."},
    },
)
def generate_admin_impact_explanation_draft(
    session: DatabaseSession,
    admin: AuthenticatedAdmin,
    settings: ApplicationSettings,
    _action: ImpactGenerationHeader,
    comparison_id: Annotated[int, Path(ge=1)],
) -> AdminImpactExplanationDraftResponse:
    comparison = get_admin_comparison(session, comparison_id)
    if comparison is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "not_found",
                "message": f"Comparison '{comparison_id}' was not found.",
                "details": [],
            },
        )
    try:
        provider = impact_provider_from_settings(settings)
        draft = generate_impact_explanation(
            session,
            comparison,
            provider=provider,
            created_by=admin.username,
        )
    except ImpactGenerationError as error:
        session.rollback()
        status_code = 503 if error.code == "impact_provider_not_configured" else 409
        raise HTTPException(
            status_code=status_code,
            detail={"code": error.code, "message": error.message, "details": []},
        ) from error
    except ImpactProviderError as error:
        session.rollback()
        raise HTTPException(
            status_code=502,
            detail={"code": error.code, "message": error.message, "details": []},
        ) from error
    session.commit()
    return impact_draft_response(draft)


@router.patch(
    "/impact-explanations/{draft_id}",
    response_model=AdminImpactExplanationDraftResponse,
    operation_id="reviewAdminImpactExplanationDraft",
    responses={
        **auth_responses,
        403: {"model": ApiError, "description": "The admin action header is invalid."},
        404: {"model": ApiError, "description": "The explanation draft was not found."},
        409: {"model": ApiError, "description": "The review cannot be recorded."},
    },
)
def review_admin_impact_explanation_draft(
    session: DatabaseSession,
    admin: AuthenticatedAdmin,
    _action: ImpactReviewHeader,
    draft_id: Annotated[str, Path(min_length=1, max_length=120)],
    request: AdminImpactExplanationReviewRequest,
) -> AdminImpactExplanationDraftResponse:
    draft = get_impact_explanation_draft(session, draft_id=draft_id)
    if draft is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "not_found",
                "message": f"Impact explanation draft '{draft_id}' was not found.",
                "details": [],
            },
        )
    try:
        record_impact_explanation_review(
            draft,
            decision=ImpactExplanationReviewDecision(request.decision),
            output=request.output,
            reviewer_name=admin.username,
        )
    except ImpactExplanationReviewError as error:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail={"code": error.code, "message": error.message, "details": []},
        ) from error
    session.commit()
    return impact_draft_response(draft)


@router.post(
    "/impact-explanations/{draft_id}/publish",
    response_model=AdminImpactExplanationDraftResponse,
    operation_id="publishAdminImpactExplanationDraft",
    responses={
        **auth_responses,
        403: {"model": ApiError, "description": "The admin action header is invalid."},
        404: {"model": ApiError, "description": "The explanation draft was not found."},
        409: {"model": ApiError, "description": "The draft is not eligible for publication."},
    },
)
def publish_admin_impact_explanation_draft(
    session: DatabaseSession,
    admin: AuthenticatedAdmin,
    _action: ImpactPublishHeader,
    draft_id: Annotated[str, Path(min_length=1, max_length=120)],
) -> AdminImpactExplanationDraftResponse:
    draft = get_impact_explanation_draft(session, draft_id=draft_id)
    if draft is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "not_found",
                "message": f"Impact explanation draft '{draft_id}' was not found.",
                "details": [],
            },
        )
    try:
        publish_approved_impact_explanation(
            session,
            draft,
            publisher_name=admin.username,
        )
    except ImpactExplanationReviewError as error:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail={"code": error.code, "message": error.message, "details": []},
        ) from error
    session.commit()
    return impact_draft_response(draft)


@router.post(
    "/comparisons/generate",
    response_model=AdminComparisonGenerationResponse,
    operation_id="generateAdminComparisons",
    responses={
        **auth_responses,
        403: {"model": ApiError, "description": "The admin action header is invalid."},
        422: {"model": ApiError, "description": "The comparison request is invalid."},
    },
)
def generate_admin_comparisons(
    session: DatabaseSession,
    _admin: AuthenticatedAdmin,
    _action: ComparisonPrepareHeader,
    request: AdminComparisonGenerationRequest,
) -> AdminComparisonGenerationResponse:
    if request.from_year == request.to_year:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "invalid_year_pair",
                "message": "Comparison years must be different.",
                "details": [],
            },
        )
    result = prepare_roster_comparisons(
        session,
        from_year=request.from_year,
        to_year=request.to_year,
    )
    session.commit()
    return result


@router.patch(
    "/comparisons/{comparison_id}",
    response_model=AdminComparisonResponse,
    operation_id="reviewAdminComparison",
    responses={
        **auth_responses,
        403: {"model": ApiError, "description": "The admin action header is invalid."},
        404: {"model": ApiError, "description": "The comparison was not found."},
        409: {"model": ApiError, "description": "The review cannot be recorded."},
    },
)
def review_admin_comparison(
    session: DatabaseSession,
    admin: AuthenticatedAdmin,
    _action: ComparisonReviewHeader,
    comparison_id: Annotated[int, Path(ge=1)],
    request: AdminComparisonDecisionRequest,
) -> AdminComparisonResponse:
    comparison = get_admin_comparison(session, comparison_id)
    if comparison is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "not_found",
                "message": f"Comparison '{comparison_id}' was not found.",
                "details": [],
            },
        )
    notes = request.reviewer_notes.strip() if request.reviewer_notes else None
    try:
        record_comparison_review(
            comparison,
            decision=ComparisonReviewDecision(request.decision),
            reviewer_name=admin.username,
            reviewer_notes=notes,
        )
    except ComparisonPublicationError as error:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail={"code": error.code, "message": error.message, "details": []},
        ) from error
    session.commit()
    refreshed = get_admin_comparison(session, comparison_id)
    assert refreshed is not None
    return admin_comparison_response(refreshed)


@router.post(
    "/comparisons/{comparison_id}/publish",
    response_model=AdminComparisonResponse,
    operation_id="publishAdminComparison",
    responses={
        **auth_responses,
        403: {"model": ApiError, "description": "The admin action header is invalid."},
        404: {"model": ApiError, "description": "The comparison was not found."},
        409: {"model": ApiError, "description": "The comparison is not publishable."},
    },
)
def publish_admin_comparison(
    session: DatabaseSession,
    admin: AuthenticatedAdmin,
    _action: ComparisonPublishHeader,
    comparison_id: Annotated[int, Path(ge=1)],
) -> AdminComparisonResponse:
    comparison = get_admin_comparison(session, comparison_id)
    if comparison is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "not_found",
                "message": f"Comparison '{comparison_id}' was not found.",
                "details": [],
            },
        )
    try:
        publish_approved_comparison(
            session,
            comparison,
            publisher_name=admin.username,
        )
    except ComparisonPublicationError as error:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail={"code": error.code, "message": error.message, "details": []},
        ) from error
    session.commit()
    refreshed = get_admin_comparison(session, comparison_id)
    assert refreshed is not None
    return admin_comparison_response(refreshed)


@router.patch(
    "/review-items/{review_item_id}",
    response_model=AdminFieldCandidateResponse,
    operation_id="reviewAdminFieldCandidate",
    responses={
        **auth_responses,
        403: {"model": ApiError, "description": "The admin action header is invalid."},
        404: {"model": ApiError, "description": "The private review item was not found."},
        409: {"model": ApiError, "description": "The review item is stale."},
        422: {"model": ApiError, "description": "The review decision is invalid."},
    },
)
def review_field_candidate(
    session: DatabaseSession,
    admin: AuthenticatedAdmin,
    _action: AdminActionHeader,
    review_item_id: Annotated[str, Path(min_length=1)],
    request: AdminCandidateDecisionRequest,
) -> AdminFieldCandidateResponse:
    candidate = get_private_candidate(session, review_item_id)
    if candidate is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "not_found",
                "message": f"Private review item '{review_item_id}' was not found.",
                "details": [],
            },
        )

    if candidate.publication_state == PublicationState.PUBLISHED:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "published_review_locked",
                "message": (
                    "A published field cannot be changed through the private review action. "
                    "Create a new source-backed revision instead."
                ),
                "details": [],
            },
        )

    decision = CandidateReviewDecision(request.decision)
    reviewed_value = request.reviewed_value.strip() if request.reviewed_value else None
    reviewer_notes = request.reviewer_notes.strip() if request.reviewer_notes else None
    if decision == CandidateReviewDecision.APPROVE and not reviewed_value:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "review_validation_error",
                "message": "An approved candidate requires a reviewed value.",
                "details": [],
            },
        )
    if decision != CandidateReviewDecision.APPROVE and not reviewer_notes:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "review_validation_error",
                "message": f"Reviewer notes are required for {decision.value}.",
                "details": [],
            },
        )
    if decision != CandidateReviewDecision.APPROVE and reviewed_value is not None:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "review_validation_error",
                "message": "Only approved candidates can contain a reviewed value.",
                "details": [],
            },
        )
    if (
        decision == CandidateReviewDecision.APPROVE
        and candidate.measure_version.newer_revision_detected
    ):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "stale_review_item",
                "message": "Approval is blocked because a newer source revision was detected.",
                "details": [],
            },
        )

    record_candidate_review(
        candidate,
        decision=decision,
        reviewed_value=reviewed_value,
        reviewer_name=admin.username,
        reviewer_notes=reviewer_notes,
    )
    session.commit()
    return candidate_response(candidate)


@router.post(
    "/review-items/{review_item_id}/publish",
    response_model=AdminFieldCandidateResponse,
    operation_id="publishAdminFieldCandidate",
    responses={
        **auth_responses,
        403: {"model": ApiError, "description": "The admin action header is invalid."},
        404: {"model": ApiError, "description": "The private review item was not found."},
        409: {"model": ApiError, "description": "The field is not publication eligible."},
    },
)
def publish_field_candidate(
    session: DatabaseSession,
    admin: AuthenticatedAdmin,
    _action: FieldPublicationHeader,
    review_item_id: Annotated[str, Path(min_length=1)],
) -> AdminFieldCandidateResponse:
    candidate = get_private_candidate(session, review_item_id)
    if candidate is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "not_found",
                "message": f"Private review item '{review_item_id}' was not found.",
                "details": [],
            },
        )
    try:
        publish_approved_field(session, candidate, publisher_name=admin.username)
    except FieldPublicationError as error:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail={"code": error.code, "message": error.message, "details": []},
        ) from error
    session.commit()
    return candidate_response(candidate)
