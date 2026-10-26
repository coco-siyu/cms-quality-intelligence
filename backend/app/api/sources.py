import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Path, status
from sqlalchemy.orm import Session

from app.auth import AdminIdentity, require_admin
from app.config import Settings, get_settings
from app.database import get_db
from app.repositories.sources import (
    get_extraction_detail,
    get_source_model,
    list_sources,
    source_detail,
)
from app.schemas import (
    AdminSourceCheckRequest,
    AdminSourceCreateRequest,
    AdminSourceDetailResponse,
    AdminSourceExtractionDetailResponse,
    AdminSourceListResponse,
    AdminSourceUpdateRequest,
    ApiError,
)
from app.services.source_ingestion import SourceFetchError, fetch_registered_source
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


SourceRegistryHeader = Annotated[None, Depends(require_source_registry_header)]
SourceCheckHeader = Annotated[None, Depends(require_source_check_header)]


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
