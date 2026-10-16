from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"]


app = FastAPI(
    title="CMS Quality Intelligence API",
    version="0.1.0",
    description="Evidence-grounded CMS quality measure intelligence API.",
)


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health() -> HealthResponse:
    """Report whether the API process is available."""
    return HealthResponse(status="ok")
