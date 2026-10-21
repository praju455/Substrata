"""Tenant derived from verified claims, never a caller-selected header or body."""

from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import AwareDatetime, Field

from substrata.platform.assistant import AssistantRequest
from substrata.platform.auth import Principal, principal, public_request
from substrata.platform.confirmations import ConfirmationInput, SupplierReply
from substrata.platform.domain import Contract, GraphData, Identifier, Provenance
from substrata.platform.governance import Policy, ProposalInput
from substrata.platform.oidc import CodeExchange
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


class ReasonInput(Contract):
    reason: str = Field(min_length=1, max_length=2000)


class ResolutionInput(ReasonInput):
    decisions: dict[str, str | None]


class ApprovalInput(ReasonInput):
    decision: str


class DelegateInput(ReasonInput):
    subject: str = Field(min_length=1, max_length=256)


class RestImport(GraphChange):
    idempotency_key: str = Field(min_length=1, max_length=96)


class EvidenceQuery(Contract):
    query: str = Field(min_length=1, max_length=2000)


class EventRuleInput(Contract):
    name: Identifier = "default"
    categories: set[Literal["supply_disruption", "weather", "transport", "sanctions", "other"]]
    minimum_severity: float = Field(default=0, ge=0, le=1, allow_inf_nan=False)
    enabled: bool = True


class EventSubmitInput(Contract):
    source_id: Identifier
    title: str = Field(min_length=1, max_length=256)
    description: str = Field(default="", max_length=10000)
    observed_at: AwareDatetime
    provenance: Provenance


class JobInput(Contract):
    kind: Literal["event_poll", "assessment", "agent_task"]
    idempotency_key: Identifier
    payload: dict = Field(default_factory=dict)


class EventResolution(Contract):
    entity_id: Identifier
    reason: str = Field(min_length=1, max_length=2000)


class AlertAcknowledgement(Contract):
    reason: str = Field(min_length=1, max_length=2000)


class PortalToken(Contract):
    token: str = Field(min_length=1, max_length=16384)


@router.get("/identity")
def identity(actor: Actor):
    return actor


@router.get("/auth/config", dependencies=[Depends(public_request)])
def auth_config():
    from substrata.platform.oidc import login_config

    return login_config()


@router.post("/auth/exchange", dependencies=[Depends(public_request)])
def auth_exchange(body: CodeExchange, request: Request):
    from substrata.platform.oidc import exchange

    return exchange(body, request.app.state.auth_verifier)


@router.get("/state")
def workspace_state(request: Request, actor: Actor):
    from sqlalchemy import select

    from substrata.platform.database import tenant_transaction
    from substrata.platform.models import Document, Organisation
    from substrata.platform.records import list_records

    actor.require("viewer")
    store = request.app.state.platform_store
    with tenant_transaction(store.engine, actor.tenant_id) as session:
        org = session.get(Organisation, actor.tenant_id)
        organisation = (
            {"name": org.name, "version": org.version, "policy": org.policy} if org else None
        )
        documents = [
            {"id": doc.id, "sha256": doc.sha256, "provenance": doc.provenance}
            for doc in session.scalars(
                select(Document).where(Document.tenant_id == actor.tenant_id).limit(200)
            )
        ]
    snapshot = store.snapshot(actor.tenant_id) if organisation and organisation["version"] else None
    if snapshot:
        from substrata.platform.quality import inventory_completeness

        quality = {"inventory": inventory_completeness(snapshot)}
    else:
        quality = {"inventory": None}
    return {
        "identity": actor,
        "organisation": organisation,
        "snapshot": snapshot,
        "records": list_records(store, actor.tenant_id),
        "documents": documents,
        "audit": store.audit(actor.tenant_id)["verification"] if organisation else None,
        "quality": quality,
    }


@router.get("/quality")
def quality(request: Request, actor: Actor):
    from substrata.platform.quality import inventory_completeness

    actor.require("viewer")
    snapshot = request.app.state.platform_store.snapshot(actor.tenant_id)
    return {"inventory": inventory_completeness(snapshot)}


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
    from substrata.platform.governance import save_assessment

    actor.require("analyst")
    return save_assessment(
        request.app.state.platform_store,
        actor,
        body.source_id,
        body.severity,
        as_of=body.as_of,
        version=body.version,
        max_depth=body.max_depth,
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


@router.get("/records")
def records(request: Request, actor: Actor, kind: str | None = None, status: str | None = None):
    from substrata.platform.records import list_records

    actor.require("viewer")
    return list_records(request.app.state.platform_store, actor.tenant_id, kind=kind, status=status)


@router.get("/records/page")
def records_page(
    request: Request,
    actor: Actor,
    kind: str | None = None,
    status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = Query(None, max_length=1024),
):
    from substrata.platform.records import record_page

    actor.require("viewer")
    try:
        return record_page(
            request.app.state.platform_store,
            actor.tenant_id,
            kind=kind,
            status=status,
            limit=limit,
            cursor=cursor,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None


@router.post("/events/subscriptions")
def event_subscription(body: EventRuleInput, request: Request, actor: Actor):
    from substrata.platform.events import EventRule, subscription

    return subscription(
        request.app.state.platform_store,
        actor,
        EventRule(
            categories=body.categories,
            minimum_severity=body.minimum_severity,
            enabled=body.enabled,
        ),
        body.name,
    )


@router.post("/events")
def event_submit(body: EventSubmitInput, request: Request, actor: Actor):
    from substrata.platform.events import EventSubmission, submit

    return submit(
        request.app.state.platform_store,
        actor,
        EventSubmission(**body.model_dump()),
    )


@router.post("/events/poll")
def event_poll(request: Request, actor: Actor):
    from substrata.platform.jobs import JobInput as DurableJobInput
    from substrata.platform.jobs import enqueue

    return enqueue(
        request.app.state.platform_store,
        actor,
        DurableJobInput(kind="event_poll", idempotency_key=f"feed-poll-{uuid4().hex}"),
    )


@router.post("/events/{id}/resolve")
def event_resolve(id: str, body: EventResolution, request: Request, actor: Actor):
    from substrata.platform.database import tenant_transaction
    from substrata.platform.models import WorkRecord

    actor.require("analyst")
    store = request.app.state.platform_store
    snapshot = store.snapshot(actor.tenant_id)
    entity = next((item for item in snapshot.data.entities if item.id == body.entity_id), None)
    if entity is None:
        raise HTTPException(404, "Event entity is unavailable in this tenant.")
    with tenant_transaction(store.engine, actor.tenant_id) as session:
        org = store.organisation(session, actor.tenant_id)
        record = session.get(WorkRecord, (actor.tenant_id, id))
        if record is None or record.kind != "event" or record.status != "needs_review":
            raise HTTPException(409, "Event is unavailable or no longer needs review.")
        payload = dict(record.payload)
        payload["resolution"] = {
            "entity_id": entity.id,
            "name": entity.name,
            "reason": body.reason,
            "actor": actor.subject,
        }
        record.payload = payload
        record.status = "matched"
        store.append(
            session,
            org,
            "event.entity.resolved",
            actor.subject,
            {"id": id, "entity_id": entity.id, "reason": body.reason},
        )
        return {"id": id, "status": record.status, "resolution": payload["resolution"]}


@router.post("/alerts/{id}/acknowledge")
def acknowledge_alert(id: str, body: AlertAcknowledgement, request: Request, actor: Actor):
    from substrata.platform.database import tenant_transaction
    from substrata.platform.models import WorkRecord
    from substrata.platform.records import encode

    actor.require("analyst")
    store = request.app.state.platform_store
    with tenant_transaction(store.engine, actor.tenant_id) as session:
        org = store.organisation(session, actor.tenant_id)
        record = session.get(WorkRecord, (actor.tenant_id, id))
        if record is None or record.kind != "alert" or record.status != "open":
            raise HTTPException(409, "Alert is unavailable or already acknowledged.")
        record.status = "acknowledged"
        record.payload = {
            **record.payload,
            "acknowledged_by": actor.subject,
            "acknowledgement_reason": body.reason,
            "acknowledged_at": datetime.now(UTC).isoformat(),
        }
        store.append(
            session,
            org,
            "event.alert.acknowledged",
            actor.subject,
            {"id": id, "reason": body.reason},
        )
        return encode(record)


@router.post("/jobs")
def job_enqueue(body: JobInput, request: Request, actor: Actor):
    from substrata.platform.jobs import JobInput as DurableJobInput
    from substrata.platform.jobs import enqueue

    return enqueue(request.app.state.platform_store, actor, DurableJobInput(**body.model_dump()))


@router.post("/jobs/dispatch")
def job_dispatch(request: Request, actor: Actor):
    from substrata.platform.jobs import run_next

    return run_next(request.app.state.platform_store, actor)


@router.get("/jobs")
def job_list(request: Request, actor: Actor):
    from substrata.platform.jobs import jobs

    actor.require("viewer")
    return jobs(request.app.state.platform_store, actor.tenant_id)


@router.post("/mcp")
def mcp(request: Request, actor: Actor, body: dict):
    from fastapi.responses import Response

    from substrata.platform.agent_protocols import handle_mcp

    result = handle_mcp(request.app.state.platform_store, actor, body)
    return Response(status_code=202) if result is None else result


@router.post("/a2a")
def a2a(request: Request, actor: Actor, body: dict):
    from substrata.platform.agent_protocols import handle_a2a

    return handle_a2a(request.app.state.platform_store, actor, body)


from substrata.platform.ingestion import TabularImport  # noqa: E402


@router.post("/imports/stage")
def stage_import(body: TabularImport, request: Request, actor: Actor):
    from substrata.platform.ingestion import stage

    actor.require("analyst")
    return stage(request.app.state.platform_store, actor.tenant_id, body, actor)


@router.post("/imports/{id}/apply")
def import_apply(id: str, request: Request, actor: Actor):
    from substrata.platform.ingestion import apply_import

    actor.require("analyst")
    return apply_import(request.app.state.platform_store, actor.tenant_id, id, actor.subject)


@router.post("/imports/{id}/resolve")
def import_resolve(id: str, body: ResolutionInput, request: Request, actor: Actor):
    from substrata.platform.ingestion import resolve_import

    actor.require("analyst")
    return resolve_import(
        request.app.state.platform_store,
        actor.tenant_id,
        id,
        body.decisions,
        actor.subject,
        body.reason,
    )


@router.post("/imports/{id}/rollback")
def import_rollback(id: str, body: ReasonInput, request: Request, actor: Actor):
    from substrata.platform.ingestion import rollback

    actor.require("admin")
    return rollback(
        request.app.state.platform_store, actor.tenant_id, id, actor.subject, body.reason
    )


@router.post("/policy")
def policy_update(body: Policy, request: Request, actor: Actor):
    from substrata.platform.governance import configure_policy

    return configure_policy(request.app.state.platform_store, actor, body)


@router.get("/policy")
def policy_read(request: Request, actor: Actor):
    from substrata.platform.database import tenant_transaction
    from substrata.platform.models import Organisation

    actor.require("viewer")
    with tenant_transaction(request.app.state.platform_store.engine, actor.tenant_id) as session:
        org = session.get(Organisation, actor.tenant_id)
        return org.policy if org else {}


@router.post("/mitigations")
def mitigation(body: ProposalInput, request: Request, actor: Actor):
    from substrata.platform.governance import propose

    return propose(request.app.state.platform_store, actor, body)


@router.post("/approvals/{id}/decision")
def action_decision(id: str, body: ApprovalInput, request: Request, actor: Actor):
    from substrata.platform.governance import decide

    return decide(request.app.state.platform_store, actor, id, body.decision, body.reason)


@router.post("/approvals/{id}/delegate")
def action_delegate(id: str, body: DelegateInput, request: Request, actor: Actor):
    from substrata.platform.governance import delegate

    return delegate(request.app.state.platform_store, actor, id, body.subject, body.reason)


@router.post("/actions/{id}/execute")
def action_execute(id: str, request: Request, actor: Actor):
    from substrata.platform.governance import execute

    return execute(request.app.state.platform_store, actor, id)


@router.post("/ingest")
def rest_ingest(body: RestImport, request: Request, actor: Actor):
    from substrata.platform.connectors import receive_graph

    return receive_graph(
        request.app.state.platform_store,
        actor,
        body.data,
        body.expected_version,
        body.idempotency_key,
    )


@router.post("/webhooks/{name}")
async def webhook(name: str, body: RestImport, request: Request, actor: Actor):
    from substrata.platform.connectors import receive_graph, verify_webhook

    verify_webhook(
        actor.tenant_id,
        name,
        await request.body(),
        request.headers.get("x-substrata-signature", ""),
    )
    return receive_graph(
        request.app.state.platform_store,
        actor,
        body.data,
        body.expected_version,
        body.idempotency_key,
        connector=name,
    )


@router.get("/connectors")
def connectors(request: Request, actor: Actor):
    from substrata.platform.connectors import configured_connectors

    actor.require("viewer")
    return [
        {"name": c.name, "resources": sorted(c.resources)}
        for c in configured_connectors(actor.tenant_id).values()
    ]


@router.post("/connectors/{name}/read/{resource}")
def connector_read(name: str, resource: str, request: Request, actor: Actor):
    from substrata.platform.connectors import (
        S4HANAODataConnector,
        configured_connectors,
        connector_source,
    )

    actor.require("analyst")
    config = configured_connectors(actor.tenant_id).get(name)
    if config is None:
        raise HTTPException(404, "Tenant connector is unavailable.")
    adapter = S4HANAODataConnector(config)
    rows = adapter.read(resource)
    return {
        "rows": rows,
        "provenance": connector_source(config, resource, synthetic=adapter.synthetic),
        "requires_mapping": True,
    }


@router.get("/exports/graph.csv")
def export_graph(request: Request, actor: Actor):
    from fastapi.responses import Response

    from substrata.platform.exports import graph_csv

    actor.require("viewer")
    snapshot = request.app.state.platform_store.snapshot(actor.tenant_id)
    return Response(
        graph_csv(snapshot),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="substrata-graph.csv"'},
    )


@router.post("/evidence/index")
def evidence_index(request: Request, actor: Actor):
    from substrata.platform.evidence import index_documents

    return index_documents(request.app.state.platform_store, actor)


@router.post("/evidence/search")
def evidence_search(body: EvidenceQuery, request: Request, actor: Actor):
    from substrata.platform.evidence import retrieve

    actor.require("viewer")
    return retrieve(request.app.state.platform_store, actor.tenant_id, body.query, actor=actor)


@router.post("/evidence/discover")
def evidence_discover(body: EvidenceQuery, request: Request, actor: Actor):
    from substrata.platform.evidence import discover

    return discover(request.app.state.platform_store, actor, body.query)


@router.post("/assistant/ask")
def assistant_ask(request: Request, actor: Actor, body: AssistantRequest):
    """Answer from tenant evidence and optional public web results without business writes."""
    from substrata.platform.assistant import ask

    actor.require("viewer")
    return ask(
        request.app.state.platform_store,
        actor.tenant_id,
        body,
        model=request.app.state.assistant_model,
        search=request.app.state.web_search,
    )


@router.post("/confirmations")
def confirmation_request(body: ConfirmationInput, request: Request, actor: Actor):
    from substrata.platform.confirmations import create_request

    return create_request(request.app.state.platform_store, actor, body)


@router.post("/supplier-portal/describe", dependencies=[Depends(public_request)])
def portal_describe(body: PortalToken, request: Request):
    from substrata.platform.confirmations import describe_request

    return describe_request(request.app.state.platform_store, body.token)


@router.post("/supplier-portal/reply", dependencies=[Depends(public_request)])
def portal_reply(body: SupplierReply, request: Request):
    from substrata.platform.confirmations import reply

    return reply(request.app.state.platform_store, body)


@router.post("/models/train")
def train_model(request: Request, actor: Actor):
    from substrata.platform.scoring import train_tenant

    return train_tenant(request.app.state.platform_store, actor)


@router.post("/models/{id}/activate")
def activate_model(id: str, request: Request, actor: Actor):
    from substrata.platform.scoring import activate

    return activate(request.app.state.platform_store, actor, id)


def install(application, store, verifier):
    from substrata.platform.agent_protocols import a2a_card
    from substrata.platform.auth import RateLimiter

    application.state.platform_store = store
    application.state.auth_verifier = verifier
    application.state.platform_rate_limiter = RateLimiter()
    application.state.platform_public_rate_limiter = RateLimiter(limit=30)
    application.include_router(router)

    @application.get("/.well-known/agent.json", tags=["agents"])
    def agent_card(request: Request):
        return a2a_card(str(request.base_url).rstrip("/"))

    @application.exception_handler(Conflict)
    async def conflict(request, exception):
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=409, content={"detail": str(exception)})
