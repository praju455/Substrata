"""Tenant derived from verified claims, never a caller-selected header or body."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import Field

from substrata.platform.auth import Principal, principal
from substrata.platform.domain import Contract, GraphData, Identifier, Provenance
from substrata.platform.store import Conflict

Actor = Annotated[Principal, Depends(principal)]

router = APIRouter(prefix="/platform", tags=["platform"])


class OrganisationInput(Contract):
    name: str = Field(min_length=1, max_length=256)


class GraphChange(Contract):
    expected_version: int = Field(ge=0)
    data: GraphData


class DocumentInput(Contract):
    id: Identifier
    text: str = Field(min_length=1, max_length=2_000_000)
    provenance: Provenance


class AssessmentInput(Contract):
    source_id: Identifier
    severity: float = Field(ge=0, le=1, allow_inf_nan=False)
    as_of: datetime
    version: int | None = Field(default=None, ge=1)
    max_depth: int = Field(default=8, ge=1, le=32)


class SeedInput(Contract):
    industry: str
    expected_version: int = Field(ge=0)
    seed: int = 42


@router.get("/identity")
def identity(actor: Actor):
    return actor


@router.post("/organisation", status_code=201)
def provision(body: OrganisationInput, request: Request, actor: Actor):
    actor.require("admin")
    request.app.state.platform_store.provision(actor.tenant_id, body.name, actor.subject)
    return {"tenant_id": actor.tenant_id, "name": body.name}


@router.get("/graph")
def graph(
    request: Request,
    actor: Actor,
    version: int | None = Query(None, ge=1),
    as_of: datetime | None = None,
):
    actor.require("viewer")
    try:
        return request.app.state.platform_store.snapshot(
            actor.tenant_id, version=version, as_of=as_of
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from None


@router.post("/graph")
def revise(body: GraphChange, request: Request, actor: Actor):
    actor.require("analyst")
    return request.app.state.platform_store.save(
        actor.tenant_id, body.data, actor.subject, expected_version=body.expected_version
    )


@router.post("/documents", status_code=201)
def document(body: DocumentInput, request: Request, actor: Actor):
    actor.require("analyst")
    sha = request.app.state.platform_store.add_document(
        actor.tenant_id, body.id, body.text, body.provenance, actor.subject
    )
    return {"id": body.id, "sha256": sha}


@router.get("/audit")
def audit(request: Request, actor: Actor, expected_head: str | None = None):
    actor.require("viewer")
    return request.app.state.platform_store.audit(actor.tenant_id, expected_head)


@router.post("/scenarios/assess")
def assess_scenario(body: AssessmentInput, request: Request, actor: Actor):
    from substrata.platform.cascade import assess

    actor.require("analyst")
    snapshot = request.app.state.platform_store.snapshot(actor.tenant_id, version=body.version)
    return assess(
        snapshot, body.source_id, body.severity, as_of=body.as_of, max_depth=body.max_depth
    )


@router.post("/seeds")
def seed(body: SeedInput, request: Request, actor: Actor):
    import os

    from substrata.platform.seeds import generate

    actor.require("admin")
    if os.environ.get("SUBSTRATA_ENV", "development") != "development":
        raise HTTPException(403, "Synthetic seed loading is restricted to development.")
    return request.app.state.platform_store.save(
        actor.tenant_id,
        generate(body.industry, seed=body.seed),
        actor.subject,
        expected_version=body.expected_version,
        event_type="synthetic.seed.loaded",
    )


def install(application, store, verifier):
    from substrata.platform.auth import RateLimiter

    application.state.platform_store = store
    application.state.auth_verifier = verifier
    application.state.platform_rate_limiter = RateLimiter()
    application.include_router(router)

    @application.exception_handler(Conflict)
    async def conflict(request, exception):
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=409, content={"detail": str(exception)})
