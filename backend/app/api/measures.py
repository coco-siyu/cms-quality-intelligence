from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.domain import AffectedField, ChangeStatus, PublicVerificationStatus
from app.repositories.measures import (
    MeasureFilters,
    get_measure,
    list_measure_versions,
    list_measures,
    list_performance_years,
)
from app.schemas import (
    ApiError,
    MeasureVersionList,
    PerformanceYearList,
    PublicMeasureDetail,
    PublicMeasurePage,
)

router = APIRouter(prefix="/api", tags=["Public measures"])
DatabaseSession = Annotated[Session, Depends(get_db)]
ApplicationSettings = Annotated[Settings, Depends(get_settings)]
validation_response = {
    422: {
        "model": ApiError,
        "description": "One or more request parameters are invalid.",
    }
}
resource_responses = {
    404: {
        "model": ApiError,
        "description": "The requested public resource was not found.",
    },
    **validation_response,
}


def _not_found(measure_id: str) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={
            "code": "not_found",
            "message": f"Public measure '{measure_id}' was not found.",
            "details": [],
        },
    )


@router.get(
    "/performance-years",
    response_model=PerformanceYearList,
    operation_id="listPerformanceYears",
)
def performance_years(
    session: DatabaseSession,
    settings: ApplicationSettings,
) -> PerformanceYearList:
    years = list_performance_years(session)
    if not years:
        years = sorted({settings.default_from_year, settings.default_to_year})
    default_from = settings.default_from_year if settings.default_from_year in years else years[0]
    default_to = settings.default_to_year if settings.default_to_year in years else years[-1]
    return PerformanceYearList(
        years=years,
        default_from_year=default_from,
        default_to_year=default_to,
    )


@router.get(
    "/measures",
    response_model=PublicMeasurePage,
    operation_id="listMeasures",
    responses=validation_response,
)
def measures(
    session: DatabaseSession,
    q: Annotated[str | None, Query(max_length=200)] = None,
    performance_year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
    from_year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
    to_year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
    change_status: ChangeStatus | None = None,
    affected_field: AffectedField | None = None,
    verification_status: PublicVerificationStatus | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> PublicMeasurePage:
    return list_measures(
        session,
        MeasureFilters(
            q=q,
            performance_year=performance_year,
            from_year=from_year,
            to_year=to_year,
            change_status=change_status,
            affected_field=affected_field,
            verification_status=verification_status,
            page=page,
            page_size=page_size,
        ),
    )


@router.get(
    "/measures/{measure_id}",
    response_model=PublicMeasureDetail,
    operation_id="getMeasure",
    responses=resource_responses,
)
def measure_detail(
    session: DatabaseSession,
    measure_id: Annotated[str, Path(min_length=1)],
    from_year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
    to_year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
) -> PublicMeasureDetail:
    result = get_measure(session, measure_id, from_year, to_year)
    if result is None:
        raise _not_found(measure_id)
    return result


@router.get(
    "/measures/{measure_id}/versions",
    response_model=MeasureVersionList,
    operation_id="listMeasureVersions",
    responses=resource_responses,
)
def measure_versions(
    session: DatabaseSession,
    measure_id: Annotated[str, Path(min_length=1)],
    performance_year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
) -> MeasureVersionList:
    versions = list_measure_versions(session, measure_id, performance_year)
    if versions is None:
        raise _not_found(measure_id)
    return MeasureVersionList(measure_id=measure_id, versions=versions)
