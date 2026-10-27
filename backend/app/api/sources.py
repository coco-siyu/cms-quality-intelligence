import hmac
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Path, status
from sqlalchemy.orm import Session

from app.auth import AdminIdentity, require_admin
from app.config import Settings, get_settings
from app.database import get_db
from app.repositories.ingestion_runs import (
    get_ingestion_run,
    ingestion_run_response,
    list_ingestion_runs,
)
from app.repositories.sources import (
    clarification_response,
    get_extraction_detail,
    get_extraction_model,
    get_normalization_model,
    get_source_model,
    list_sources,
    normalization_detail,
    source_detail,
)
from app.schemas import (
    AdminClarificationProposalResponse,
    AdminIngestionRunListResponse,
    AdminIngestionRunResponse,
    AdminSourceCheckRequest,
    AdminSourceCreateRequest,
    AdminSourceDetailResponse,
    AdminSourceExtractionDetailResponse,
    AdminSourceListResponse,
    AdminSourceNormalizationDetailResponse,
    AdminSourceUpdateRequest,
    ApiError,
)
from app.services.ai_clarification import (
    ClarificationError,
    clarify_unresolved_field,
    get_normalized_field,
    provider_from_settings,
)
from app.services.ingestion_runs import (
    IngestionRunError,
    create_ingestion_run,
    execute_ingestion_run_by_id,
)
from app.services.source_ingestion import SourceFetchError, fetch_registered_source
from app.services.source_normalization import (
    SourceNormalizationError,
    normalize_extraction,
)
from app.services.source_registry import (
    SourceRegistryError,
    create_source,
    update_source,
)

router = APIRouter(prefix="/api/admin", tags=["Admin sources"])
DatabaseSession = Annotated[Session, Depends(get_db)]
ApplicationSettings = Annotated[Settings, Depends(get_settings)]
AuthenticatedAdmin = Annotated[AdminIdentity, Depends(require_admin)]
auth_responses = {
    401: {"model": ApiError, "description": "Administrator authentication is required."}
}


def _require_action(expected: str, actual: str) -> None:
    if not hmac.compare_digest(actual, expected):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "invalid_admin_action_header",
                "message": "The required administrator action header is invalid.",
                "details": [],
            },
        )


def require_source_registry_header(
    action: Annotated[str, Header(alias="X-CMSQI-Admin-Action")],
) -> None:
    _require_action("source-registry", action)


def require_source_check_header(
    action: Annotated[str, Header(alias="X-CMSQI-Admin-Action")],
) -> None:
    _require_action("source-check", action)


def require_source_normalization_header(
    action: Annotated[str, Header(alias="X-CMSQI-Admin-Action")],
) -> None:
    _require_action("normalize-source", action)


def require_source_clarification_header(
    action: Annotated[str, Header(alias="X-CMSQI-Admin-Action")],
) -> None:
    _require_action("clarify-source", action)


def require_ingestion_run_header(
    action: Annotated[str, Header(alias="X-CMSQI-Admin-Action")],
) -> None:
    _require_action("check-for-updates", action)


SourceRegistryHeader = Annotated[None, Depends(require_source_registry_header)]
SourceCheckHeader = Annotated[None, Depends(require_source_check_header)]
SourceNormalizationHeader = Annotated[
    None, Depends(require_source_normalization_header)
]
SourceClarificationHeader = Annotated[
    None, Depends(require_source_clarification_header)
]
IngestionRunHeader = Annotated[None, Depends(require_ingestion_run_header)]


def _not_found(source_id: str) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={
            "code": "not_found",
            "message": f"CMS source '{source_id}' was not found.",
            "details": [],
        },
    )


def _registry_error(error: SourceRegistryError) -> HTTPException:
    status_code = 409 if error.code.endswith("_conflict") else 422
    return HTTPException(
        status_code=status_code,
        detail={"code": error.code, "message": error.message, "details": []},
    )


@router.get(
    "/sources",
    response_model=AdminSourceListResponse,
    operation_id="listAdminSources",
    responses=auth_responses,
)
def admin_sources(
    session: DatabaseSession, _admin: AuthenticatedAdmin
) -> AdminSourceListResponse:
    return list_sources(session)


@router.get(
    "/ingestion-runs",
    response_model=AdminIngestionRunListResponse,
    operation_id="listAdminIngestionRuns",
    responses=auth_responses,
)
def admin_ingestion_runs(
    session: DatabaseSession, _admin: AuthenticatedAdmin
) -> AdminIngestionRunListResponse:
    return list_ingestion_runs(session)


@router.get(
    "/ingestion-runs/{run_id}",
    response_model=AdminIngestionRunResponse,
    operation_id="getAdminIngestionRun",
    responses={**auth_responses, 404: {"model": ApiError}},
)
def admin_ingestion_run(
    session: DatabaseSession,
    _admin: AuthenticatedAdmin,
    run_id: Annotated[str, Path(min_length=1, max_length=120)],
) -> AdminIngestionRunResponse:
    run = get_ingestion_run(session, run_id)
    if run is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "not_found",
                "message": f"Ingestion run '{run_id}' was not found.",
                "details": [],
            },
        )
    return ingestion_run_response(run)


@router.post(
    "/ingestion-runs",
    response_model=AdminIngestionRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="createAdminIngestionRun",
    responses={
        **auth_responses,
        403: {"model": ApiError},
        409: {"model": ApiError},
    },
)
def create_admin_ingestion_run(
    background_tasks: BackgroundTasks,
    session: DatabaseSession,
    settings: ApplicationSettings,
    admin: AuthenticatedAdmin,
    _action: IngestionRunHeader,
) -> AdminIngestionRunResponse:
    try:
        run = create_ingestion_run(
            session,
            created_by=admin.username,
            max_sources=settings.ingestion_run_max_sources,
        )
        run_id = run.run_id
        session.commit()
    except IngestionRunError as error:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail={"code": error.code, "message": error.message, "details": []},
        ) from error
    refreshed = get_ingestion_run(session, run_id)
    if refreshed is None:  # pragma: no cover - the run is committed before retrieval
        raise HTTPException(status_code=404, detail="Ingestion run was not found.")
    response = ingestion_run_response(refreshed)
    background_tasks.add_task(
        execute_ingestion_run_by_id,
        run_id,
        settings=settings,
        checked_by=admin.username,
    )
    return response


@router.post(
    "/sources",
    response_model=AdminSourceDetailResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createAdminSource",
    responses={**auth_responses, 403: {"model": ApiError}, 409: {"model": ApiError}},
)
def create_admin_source(
    request: AdminSourceCreateRequest,
    session: DatabaseSession,
    admin: AuthenticatedAdmin,
    _action: SourceRegistryHeader,
) -> AdminSourceDetailResponse:
    try:
        source = create_source(
            session,
            source_id=request.source_id,
            title=request.title,
            official_url=str(request.official_url),
            source_format=request.source_format,
            notes=request.notes,
            admin_username=admin.username,
        )
    except SourceRegistryError as error:
        raise _registry_error(error) from error
    session.commit()
    refreshed = get_source_model(session, source.source_id)
    if refreshed is None:  # pragma: no cover - committed row must be queryable
        raise _not_found(source.source_id)
    return source_detail(refreshed)


@router.get(
    "/sources/{source_id}",
    response_model=AdminSourceDetailResponse,
    operation_id="getAdminSource",
    responses={**auth_responses, 404: {"model": ApiError}},
)
def admin_source_detail(
    session: DatabaseSession,
    _admin: AuthenticatedAdmin,
    source_id: Annotated[str, Path(min_length=1, max_length=100)],
) -> AdminSourceDetailResponse:
    source = get_source_model(session, source_id)
    if source is None:
        raise _not_found(source_id)
    return source_detail(source)


@router.patch(
    "/sources/{source_id}",
    response_model=AdminSourceDetailResponse,
    operation_id="updateAdminSource",
    responses={
        **auth_responses,
        403: {"model": ApiError},
        404: {"model": ApiError},
        409: {"model": ApiError},
    },
)
def update_admin_source(
    request: AdminSourceUpdateRequest,
    session: DatabaseSession,
    _admin: AuthenticatedAdmin,
    _action: SourceRegistryHeader,
    source_id: Annotated[str, Path(min_length=1, max_length=100)],
) -> AdminSourceDetailResponse:
    source = get_source_model(session, source_id)
    if source is None:
        raise _not_found(source_id)
    try:
        update_source(
            session,
            source,
            title=request.title,
            official_url=(
                str(request.official_url) if request.official_url is not None else None
            ),
            source_format=request.source_format,
            notes=request.notes,
            update_notes="notes" in request.model_fields_set,
            is_active=request.is_active,
        )
    except SourceRegistryError as error:
        raise _registry_error(error) from error
    session.commit()
    refreshed = get_source_model(session, source_id)
    if refreshed is None:  # pragma: no cover - updates do not delete rows
        raise _not_found(source_id)
    return source_detail(refreshed)


@router.post(
    "/sources/{source_id}/check",
    response_model=AdminSourceDetailResponse,
    operation_id="checkAdminSource",
    responses={
        **auth_responses,
        403: {"model": ApiError},
        404: {"model": ApiError},
        409: {"model": ApiError},
        502: {"model": ApiError},
    },
)
def check_admin_source(
    request: AdminSourceCheckRequest,
    session: DatabaseSession,
    settings: ApplicationSettings,
    admin: AuthenticatedAdmin,
    _action: SourceCheckHeader,
    source_id: Annotated[str, Path(min_length=1, max_length=100)],
) -> AdminSourceDetailResponse:
    source = get_source_model(session, source_id)
    if source is None:
        raise _not_found(source_id)
    try:
        fetch_registered_source(
            session,
            source,
            settings=settings,
            checked_by=admin.username,
            force=request.force,
        )
    except SourceFetchError as error:
        session.commit()
        status_code = 409 if error.code == "source_inactive" else 502
        raise HTTPException(
            status_code=status_code,
            detail={"code": error.code, "message": error.message, "details": []},
        ) from error
    session.commit()
    refreshed = get_source_model(session, source_id)
    if refreshed is None:  # pragma: no cover - checks do not delete rows
        raise _not_found(source_id)
    return source_detail(refreshed)


@router.get(
    "/source-extractions/{extraction_id}",
    response_model=AdminSourceExtractionDetailResponse,
    operation_id="getAdminSourceExtraction",
    responses={**auth_responses, 404: {"model": ApiError}},
)
def admin_source_extraction(
    session: DatabaseSession,
    _admin: AuthenticatedAdmin,
    extraction_id: Annotated[str, Path(min_length=1, max_length=200)],
) -> AdminSourceExtractionDetailResponse:
    extraction = get_extraction_detail(session, extraction_id)
    if extraction is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "not_found",
                "message": f"Source extraction '{extraction_id}' was not found.",
                "details": [],
            },
        )
    return extraction


@router.post(
    "/source-extractions/{extraction_id}/normalize",
    response_model=AdminSourceNormalizationDetailResponse,
    operation_id="normalizeAdminSourceExtraction",
    responses={
        **auth_responses,
        403: {"model": ApiError},
        404: {"model": ApiError},
        409: {"model": ApiError},
    },
)
def normalize_admin_source_extraction(
    session: DatabaseSession,
    admin: AuthenticatedAdmin,
    _action: SourceNormalizationHeader,
    extraction_id: Annotated[str, Path(min_length=1, max_length=200)],
) -> AdminSourceNormalizationDetailResponse:
    extraction = get_extraction_model(session, extraction_id)
    if extraction is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "not_found",
                "message": f"Source extraction '{extraction_id}' was not found.",
                "details": [],
            },
        )
    try:
        normalization = normalize_extraction(
            session, extraction, created_by=admin.username
        )
    except SourceNormalizationError as error:
        raise HTTPException(
            status_code=409,
            detail={"code": error.code, "message": error.message, "details": []},
        ) from error
    normalization_id = normalization.normalization_id
    session.commit()
    refreshed = get_normalization_model(session, normalization_id)
    if refreshed is None:  # pragma: no cover - committed row must be queryable
        raise HTTPException(status_code=404, detail="Normalization was not found.")
    return normalization_detail(refreshed)


@router.get(
    "/source-normalizations/{normalization_id}",
    response_model=AdminSourceNormalizationDetailResponse,
    operation_id="getAdminSourceNormalization",
    responses={**auth_responses, 404: {"model": ApiError}},
)
def admin_source_normalization(
    session: DatabaseSession,
    _admin: AuthenticatedAdmin,
    normalization_id: Annotated[str, Path(min_length=1, max_length=120)],
) -> AdminSourceNormalizationDetailResponse:
    normalization = get_normalization_model(session, normalization_id)
    if normalization is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "not_found",
                "message": f"Source normalization '{normalization_id}' was not found.",
                "details": [],
            },
        )
    return normalization_detail(normalization)


@router.post(
    "/normalized-fields/{field_candidate_id}/clarifications",
    response_model=AdminClarificationProposalResponse,
    operation_id="clarifyAdminNormalizedField",
    responses={
        **auth_responses,
        403: {"model": ApiError},
        404: {"model": ApiError},
        409: {"model": ApiError},
        502: {"model": ApiError},
        503: {"model": ApiError},
    },
)
def clarify_admin_normalized_field(
    session: DatabaseSession,
    settings: ApplicationSettings,
    admin: AuthenticatedAdmin,
    _action: SourceClarificationHeader,
    field_candidate_id: Annotated[str, Path(min_length=1, max_length=120)],
) -> AdminClarificationProposalResponse:
    field = get_normalized_field(session, field_candidate_id)
    if field is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "not_found",
                "message": f"Normalized field '{field_candidate_id}' was not found.",
                "details": [],
            },
        )
    try:
        provider = provider_from_settings(settings)
        proposal = clarify_unresolved_field(
            session,
            field,
            provider=provider,
            created_by=admin.username,
            max_excerpts=settings.ai_clarification_max_excerpts,
            max_input_chars=settings.ai_clarification_max_input_chars,
        )
    except ClarificationError as error:
        if error.code == "clarification_provider_not_configured":
            status_code = 503
        elif error.code.startswith("clarification_provider_"):
            status_code = 502
        else:
            status_code = 409
        raise HTTPException(
            status_code=status_code,
            detail={"code": error.code, "message": error.message, "details": []},
        ) from error
    clarification_id = proposal.clarification_id
    session.commit()
    refreshed_field = get_normalized_field(session, field_candidate_id)
    if refreshed_field is None:  # pragma: no cover - clarification cannot delete its field
        raise HTTPException(status_code=404, detail="Normalized field was not found.")
    refreshed = next(
        item
        for item in refreshed_field.clarifications
        if item.clarification_id == clarification_id
    )
    return clarification_response(refreshed)
