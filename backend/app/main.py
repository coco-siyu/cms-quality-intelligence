from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.admin import router as admin_router
from app.api.measures import router as measures_router
from app.schemas import ApiError, HealthResponse


def create_app() -> FastAPI:
    application = FastAPI(
        title="CMS Quality Intelligence API",
        version="0.1.0",
        description="Evidence-grounded CMS quality measure intelligence API.",
    )
    application.include_router(measures_router)
    application.include_router(admin_router)

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request, exception: RequestValidationError
    ) -> JSONResponse:
        error = ApiError(
            code="validation_error",
            message="One or more request parameters are invalid.",
            details=exception.errors(),
        )
        return JSONResponse(status_code=422, content=error.model_dump(mode="json"))

    @application.exception_handler(HTTPException)
    async def http_error_handler(_request: Request, exception: HTTPException) -> JSONResponse:
        if isinstance(exception.detail, dict) and {
            "code",
            "message",
        }.issubset(exception.detail):
            error = ApiError.model_validate(exception.detail)
        else:
            error = ApiError(code="http_error", message=str(exception.detail))
        return JSONResponse(
            status_code=exception.status_code,
            content=error.model_dump(mode="json"),
            headers=exception.headers,
        )

    return application


app = create_app()


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    operation_id="getHealth",
)
async def health() -> HealthResponse:
    """Report whether the API process is available."""
    return HealthResponse(status="ok")
