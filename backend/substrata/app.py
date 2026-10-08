"""FastAPI entry point and process health contract."""

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Process liveness only; this does not assert database or scenario readiness."""

    status: Literal["ok"] = "ok"
    service: Literal["substrata-api"] = "substrata-api"
    data_mode: Literal["synthetic"] = "synthetic"


def create_app() -> FastAPI:
    """Build an independent API instance without database or network side effects."""
    application = FastAPI(
        title="Substrata API",
        version="0.1.0",
        description="Synthetic demo data. All eventual operational actions are simulated.",
    )

    @application.get("/health", response_model=HealthResponse, tags=["system"])
    async def health() -> HealthResponse:
        """Report that the API process is responding in synthetic demo mode."""
        return HealthResponse()

    return application


app = create_app()
