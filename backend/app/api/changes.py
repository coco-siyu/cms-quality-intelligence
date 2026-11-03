from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.domain import AffectedField, ChangeStatus, CollectionType
from app.repositories.changes import ChangeFilters, get_public_change, list_public_changes
from app.schemas import ApiError, PublicChangePage, PublicChangeRecord

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
