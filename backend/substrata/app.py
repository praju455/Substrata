"""FastAPI entry point and process health contract."""

import os
import threading
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from substrata.api import router


class HealthResponse(BaseModel):
    """Process liveness only; this does not assert database or scenario readiness."""

    status: Literal["ok"] = "ok"
    service: Literal["substrata-api"] = "substrata-api"
    data_mode: Literal["synthetic"] = "synthetic"


def create_app(runtime=None) -> FastAPI:
    """Build an independent API instance without database or network side effects."""

    @asynccontextmanager
    async def lifespan(application):
        yield
        current = application.state.runtime
        if current is not None:
            current.active = False
            if current.task is not None:
                await current.task
            if runtime is None:
                current.engine.dispose()

    application = FastAPI(
        title="Substrata API",
        version="0.1.0",
        lifespan=lifespan,
        description="Synthetic demo data. All eventual operational actions are simulated.",
    )
    application.state.runtime = runtime
    application.state.runtime_lock = threading.Lock()
    ui_port = os.environ.get("SUBSTRATA_UI_PORT", "3000")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[f"http://127.0.0.1:{ui_port}", f"http://localhost:{ui_port}"],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Last-Event-ID"],
    )
    application.include_router(router)

    @application.exception_handler(ValueError)
    async def invalid_request(request, exception):
        return JSONResponse(status_code=409, content={"detail": str(exception)})

    @application.get("/health", response_model=HealthResponse, tags=["system"])
    async def health() -> HealthResponse:
        """Report that the API process is responding in synthetic demo mode."""
        return HealthResponse()

    return application


app = create_app()
