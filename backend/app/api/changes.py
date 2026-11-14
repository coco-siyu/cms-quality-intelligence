from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.domain import (
    AffectedField,
    ChangeStatus,
    CollectionType,
    PublicVerificationStatus,
)
from app.repositories.changes import (
    ChangeFilters,
    get_public_change,
    list_public_changes,
    list_public_changes_for_export,
)
from app.repositories.measures import MeasureFilters
from app.repositories.public_impact_explanations import get_public_impact_explanation
from app.schemas import ApiError, PublicChangePage, PublicChangeRecord, PublicImpactExplanation
from app.services.change_export import (
    XLSX_MEDIA_TYPE,
    build_public_change_csv,
    build_public_change_xlsx,
)

router = APIRouter(prefix="/api/changes", tags=["Public changes"])
DatabaseSession = Annotated[Session, Depends(get_db)]
validation_response = {
    422: {
        "model": ApiError,
        "description": "One or more request parameters are invalid.",
    }
}
resource_responses = {
    404: {
        "model": ApiError,
        "description": "The requested public comparison was not found.",
    },
    **validation_response,
}


def _validate_year_pair(from_year: int | None, to_year: int | None) -> None:
    if from_year is not None and to_year is not None and from_year == to_year:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "validation_error",
                "message": "The comparison years must be different.",
                "details": [],
            },
        )


def _export_records(
    session: Session,
    *,
    q: str | None,
    performance_year: int | None,
    from_year: int | None,
    to_year: int | None,
    change_status: ChangeStatus | None,
    affected_field: AffectedField | None,
    verification_status: PublicVerificationStatus | None,
    collection_type: CollectionType | None,
) -> list[PublicChangeRecord]:
    measure_filters = MeasureFilters(
        q=q,
        performance_year=performance_year,
        from_year=from_year,
        to_year=to_year,
        change_status=change_status,
        affected_field=affected_field,
        verification_status=verification_status,
    )
    return list_public_changes_for_export(
        session,
        change_filters=ChangeFilters(
            from_year=from_year,
            to_year=to_year,
            change_status=change_status,
            affected_field=affected_field,
            collection_type=collection_type,
        ),
        measure_filters=measure_filters,
    )


def _export_filename(extension: str, from_year: int | None, to_year: int | None) -> str:
    year_suffix = (
        f"-{from_year}-{to_year}" if from_year is not None and to_year is not None else ""
    )
    return f"cms-quality-changes{year_suffix}.{extension}"


@router.get(
    "",
    response_model=PublicChangePage,
    operation_id="listChanges",
    responses=validation_response,
)
def changes(
    session: DatabaseSession,
    from_year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
    to_year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
    change_status: ChangeStatus | None = None,
    affected_field: AffectedField | None = None,
    collection_type: CollectionType | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> PublicChangePage:
    _validate_year_pair(from_year, to_year)
    return list_public_changes(
        session,
        ChangeFilters(
            from_year=from_year,
            to_year=to_year,
            change_status=change_status,
            affected_field=affected_field,
            collection_type=collection_type,
            page=page,
            page_size=page_size,
        ),
    )


@router.get(
    "/export.csv",
    operation_id="exportChangesCsv",
    response_class=Response,
    responses={
        200: {
            "description": "CSV rows for the filtered, verified public comparison fields.",
            "content": {"text/csv": {"schema": {"type": "string"}}},
        },
        **validation_response,
    },
)
def export_changes_csv(
    session: DatabaseSession,
    q: Annotated[str | None, Query(max_length=200)] = None,
    performance_year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
    from_year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
    to_year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
    change_status: ChangeStatus | None = None,
    affected_field: AffectedField | None = None,
    verification_status: PublicVerificationStatus | None = None,
    collection_type: CollectionType | None = None,
) -> Response:
    _validate_year_pair(from_year, to_year)
    records = _export_records(
        session,
        q=q,
        performance_year=performance_year,
        from_year=from_year,
        to_year=to_year,
        change_status=change_status,
        affected_field=affected_field,
        verification_status=verification_status,
        collection_type=collection_type,
    )
    return Response(
        content=build_public_change_csv(records, affected_field=affected_field),
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{_export_filename("csv", from_year, to_year)}"'
            )
        },
    )


@router.get(
    "/export.xlsx",
    operation_id="exportChangesXlsx",
    response_class=Response,
    responses={
        200: {
            "description": "XLSX workbook for filtered, verified public comparison fields.",
            "content": {XLSX_MEDIA_TYPE: {"schema": {"type": "string", "format": "binary"}}},
        },
        **validation_response,
    },
)
def export_changes_xlsx(
    session: DatabaseSession,
    q: Annotated[str | None, Query(max_length=200)] = None,
    performance_year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
    from_year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
    to_year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
    change_status: ChangeStatus | None = None,
    affected_field: AffectedField | None = None,
    verification_status: PublicVerificationStatus | None = None,
    collection_type: CollectionType | None = None,
) -> Response:
    _validate_year_pair(from_year, to_year)
    records = _export_records(
        session,
        q=q,
        performance_year=performance_year,
        from_year=from_year,
        to_year=to_year,
        change_status=change_status,
        affected_field=affected_field,
        verification_status=verification_status,
        collection_type=collection_type,
    )
    return Response(
        content=build_public_change_xlsx(records, affected_field=affected_field),
        media_type=XLSX_MEDIA_TYPE,
        headers={
            "Content-Disposition": (
                f'attachment; filename="{_export_filename("xlsx", from_year, to_year)}"'
            )
        },
    )


@router.get(
    "/{measure_id}",
    response_model=PublicChangeRecord,
    operation_id="getChange",
    responses=resource_responses,
)
def change_detail(
    session: DatabaseSession,
    measure_id: Annotated[str, Path(min_length=1)],
    program: Annotated[str, Query(min_length=1, max_length=120)],
    collection_type: CollectionType,
    from_year: Annotated[int, Query(ge=2000, le=2100)],
    to_year: Annotated[int, Query(ge=2000, le=2100)],
) -> PublicChangeRecord:
    _validate_year_pair(from_year, to_year)
    result = get_public_change(
        session,
        measure_id=measure_id,
        program=program,
        collection_type=collection_type,
        from_year=from_year,
        to_year=to_year,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "not_found",
                "message": f"Public comparison for '{measure_id}' was not found.",
                "details": [],
            },
        )
    return result


@router.get(
    "/{measure_id}/impact-explanation",
    response_model=PublicImpactExplanation,
    operation_id="getImpactExplanation",
    responses=resource_responses,
)
def impact_explanation_detail(
    session: DatabaseSession,
    measure_id: Annotated[str, Path(min_length=1)],
    program: Annotated[str, Query(min_length=1, max_length=120)],
    collection_type: CollectionType,
    from_year: Annotated[int, Query(ge=2000, le=2100)],
    to_year: Annotated[int, Query(ge=2000, le=2100)],
) -> PublicImpactExplanation:
    _validate_year_pair(from_year, to_year)
    result = get_public_impact_explanation(
        session,
        measure_id=measure_id,
        program=program,
        collection_type=collection_type,
        from_year=from_year,
        to_year=to_year,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "not_found",
                "message": f"Public impact explanation for '{measure_id}' was not found.",
                "details": [],
            },
        )
    return result
