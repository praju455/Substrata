"""FastAPI entry point and process health contract."""

import os
import threading
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel
from sqlalchemy import text

from substrata.api import router
from substrata.observability import (
    HTTPMetrics,
    HTTPObservability,
    configure_logging,
    configured_tracing,
)


class HealthResponse(BaseModel):
    """Process liveness only; this does not assert database or scenario readiness."""

    status: Literal["ok"] = "ok"
    service: Literal["substrata-api"] = "substrata-api"
    data_mode: Literal["synthetic"] = "synthetic"


class TenantHealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: Literal["substrata-api"] = "substrata-api"
    data_mode: Literal["tenant"] = "tenant"


def create_app(runtime=None, *, platform_store=None, auth_verifier=None, tracing=None) -> FastAPI:
    """Build an independent API instance without database or network side effects."""

    @asynccontextmanager
    async def lifespan(application):
        try:
            yield
        finally:
            try:
                current = application.state.runtime
                if current is not None:
                    current.active = False
                    if current.task is not None:
                        await current.task
                    if runtime is None:
                        current.engine.dispose()
                if platform_store is None and getattr(application.state, "platform_store", None):
                    application.state.platform_store.engine.dispose()
            finally:
                application.state.tracing.shutdown()

    application = FastAPI(
        title="Substrata API",
        version="0.1.0",
        lifespan=lifespan,
        description="Synthetic demo data. All eventual operational actions are simulated.",
    )
    application.state.runtime = runtime
    configure_logging()
    application.state.runtime_lock = threading.Lock()
    application.state.tracing = tracing or configured_tracing()
    application.state.http_metrics = HTTPMetrics()
    ui_port = os.environ.get("SUBSTRATA_UI_PORT", "3000")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=os.environ.get(
            "SUBSTRATA_CORS_ORIGINS", f"http://127.0.0.1:{ui_port},http://localhost:{ui_port}"
        ).split(","),
        allow_methods=["GET", "POST"],
        allow_headers=[
            "Content-Type",
            "Last-Event-ID",
            "Authorization",
            "X-Request-ID",
            "traceparent",
        ],
        expose_headers=["X-Request-ID", "traceparent"],
    )

    application.add_middleware(
        HTTPObservability, tracing=application.state.tracing, metrics=application.state.http_metrics
    )

    platform_enabled = (
        platform_store is not None or os.environ.get("SUBSTRATA_PLATFORM_ENABLED") == "true"
    )
    demo_enabled = (
        runtime is not None
        or os.environ.get("SUBSTRATA_DEMO_ENABLED", "false" if platform_enabled else "true")
        == "true"
    )
    if demo_enabled:
        if platform_enabled and os.environ.get("SUBSTRATA_ENV", "development") != "development":
            raise ValueError("The unauthenticated synthetic demo is disabled outside development.")
        application.include_router(router)
    if platform_enabled:
        application.description = "Tenant supply-chain platform. Execution defaults to dry-run."
        from substrata.platform.api import install
        from substrata.platform.auth import configured_verifier
        from substrata.platform.database import build_engine as platform_engine
        from substrata.platform.store import PlatformStore

        if platform_store is None:
            database_url = os.environ["SUBSTRATA_PLATFORM_DATABASE_URL"]
            if os.environ.get(
                "SUBSTRATA_ENV", "development"
            ) != "development" and not database_url.startswith("postgresql+psycopg://"):
                raise ValueError("Production platform mode requires PostgreSQL.")
            platform_store_instance = PlatformStore(platform_engine(database_url))
        else:
            platform_store_instance = platform_store
        install(application, platform_store_instance, auth_verifier or configured_verifier())

    @application.exception_handler(ValueError)
    async def invalid_request(request, exception):
        return JSONResponse(status_code=409, content={"detail": str(exception)})

    health_model = TenantHealthResponse if platform_enabled else HealthResponse

    @application.get("/health", response_model=health_model, tags=["system"])
    async def health():
        """Process liveness; business/database readiness is checked separately."""
        return health_model()

    @application.get("/ready", tags=["system"])
    async def readiness():
        dependencies = {}
        platform_store_instance = getattr(application.state, "platform_store", None)
        runtime_instance = application.state.runtime
        engines = {
            "platform_database": getattr(platform_store_instance, "engine", None),
            "demo_database": getattr(runtime_instance, "engine", None),
        }
        for name, engine in engines.items():
            if engine is None:
                dependencies[name] = "not_configured"
                continue
            try:
                with engine.connect() as connection:
                    connection.execute(text("SELECT 1"))
                dependencies[name] = "ok"
            except Exception as error:
                dependencies[name] = type(error).__name__
                raise HTTPException(
                    503, detail={"status": "not_ready", "dependencies": dependencies}
                ) from None
        return {"status": "ok", "dependencies": dependencies}

    @application.get("/metrics", response_class=PlainTextResponse, tags=["system"])
    async def metrics():
        return application.state.http_metrics.render()

    return application


app = create_app()
