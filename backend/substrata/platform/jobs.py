"""Durable tenant job records with bounded leases, retries and typed handlers."""

import hashlib
import json
import logging
import math
import os
import time
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import uuid4

from opentelemetry.trace import SpanKind, Status, StatusCode
from pydantic import AwareDatetime, Field, TypeAdapter, model_validator
from sqlalchemy import func, or_, select

from substrata.observability import operation_span, parent_context, trace_headers
from substrata.platform.database import tenant_transaction
from substrata.platform.deadlines import JobDeadlineExceeded, job_deadline, require_time
from substrata.platform.domain import Contract, Identifier
from substrata.platform.models import WorkRecord
from substrata.platform.records import add, encode, list_records
from substrata.seed import canonical

MAX_ATTEMPTS = 4
MAX_ACTIVE_JOBS_PER_TENANT = 100
JOB_TYPES = {"event_poll", "assessment", "agent_task", "agent_plan"}
LEASE = timedelta(minutes=2)
RETRY = (5, 30, 120)
DEFAULT_JOB_HOURLY_LIMIT = 100
DEFAULT_JOB_TIMEOUT_SECONDS = 120


class LeaseLost(RuntimeError):
    """The worker no longer owns this attempt and must not update its job state."""


def _require_claim(session, tenant_id, job_id, claim, *, check_deadline=True):
    record = session.scalar(
        select(WorkRecord)
        .where(WorkRecord.tenant_id == tenant_id, WorkRecord.id == job_id)
        .with_for_update()
    )
    if (
        record is None
        or record.kind != "job"
        or record.status != "running"
        or not claim.get("claim_id")
        or record.payload.get("claim_id") != claim["claim_id"]
        or record.payload["attempts"] != claim["attempts"]
        or not record.payload.get("lease_until")
        or datetime.fromisoformat(record.payload["lease_until"]) <= datetime.now(UTC)
    ):
        raise LeaseLost("Job attempt is no longer owned by this worker.")
    deadline_expired = datetime.fromisoformat(record.payload["deadline_at"]) <= datetime.now(UTC)
    if check_deadline and deadline_expired:
        raise JobDeadlineExceeded("Whole-job deadline exceeded.")
    return record


def _lost_claim(job_id, payload):
    return {"id": job_id, "status": "lease_lost", "attempt": payload["attempts"]}


class JobInput(Contract):
    kind: Literal["event_poll", "assessment", "agent_task", "agent_plan"]
    idempotency_key: Identifier
    payload: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def valid_payload(self):
        if self.kind == "event_poll" and self.payload:
            raise ValueError("Event poll jobs do not accept caller data.")
        if self.kind == "assessment":
            assessment = self.payload.get("assessment")
            if (
                set(self.payload) != {"graph_version", "assessment"}
                or isinstance(self.payload.get("graph_version"), bool)
                or not isinstance(self.payload.get("graph_version"), int)
                or self.payload["graph_version"] < 1
            ):
                raise ValueError("Assessment job requires a graph version and typed assessment.")
            expected = {"source_id", "severity", "as_of", "max_depth"}
            if not isinstance(assessment, dict) or set(assessment) != expected:
                raise ValueError("Assessment job fields are incomplete or unknown.")
            if (
                not isinstance(assessment["source_id"], str)
                or isinstance(assessment["severity"], bool)
                or not isinstance(assessment["severity"], int | float)
                or not math.isfinite(assessment["severity"])
                or not 0 <= assessment["severity"] <= 1
                or isinstance(assessment["max_depth"], bool)
                or not isinstance(assessment["max_depth"], int)
                or not 1 <= assessment["max_depth"] <= 32
            ):
                raise ValueError("Assessment job parameters are outside their valid ranges.")
            from pydantic import TypeAdapter

            TypeAdapter(Identifier).validate_python(assessment["source_id"])
            TypeAdapter(AwareDatetime).validate_python(assessment["as_of"])
        if self.kind == "agent_task":
            if set(self.payload) != {"agent", "arguments"}:
                raise ValueError("Agent task requires a registered agent and typed arguments.")
            from substrata.platform.agent_protocols import AGENT_TASK_TO_TOOL, _tool_definitions

            agent = self.payload["agent"]
            arguments = self.payload["arguments"]
            tool = AGENT_TASK_TO_TOOL.get(agent) if isinstance(agent, str) else None
            if tool is None or not isinstance(arguments, dict):
                raise ValueError("Agent task name or arguments are invalid.")
            model = _tool_definitions()[tool][0]
            model.model_validate(arguments)
            if len(canonical(self.payload).encode()) > 65_536:
                raise ValueError("Agent task input exceeds the configured size limit.")
        if self.kind == "agent_plan":
            if set(self.payload) != {"plan", "arguments"} or self.payload["plan"] != "risk_review":
                raise ValueError("Agent plan is not registered or its fields are invalid.")
            from substrata.platform.agent_protocols import AssessmentArguments

            arguments = self.payload["arguments"]
            if not isinstance(arguments, dict):
                raise ValueError("Risk review requires typed assessment arguments.")
            AssessmentArguments.model_validate(arguments)
            graph_version = arguments.get("graph_version")
            if (
                isinstance(graph_version, bool)
                or not isinstance(graph_version, int)
                or graph_version < 1
            ):
                raise ValueError("Risk review must pin an explicit graph version.")
            if len(canonical(self.payload).encode()) > 65_536:
                raise ValueError("Agent plan input exceeds the configured size limit.")
        return self


class AgentPlanResume(Contract):
    checkpoint: Literal["relationship_review", "approval"]
    reason: str = Field(min_length=1, max_length=2000)


def enqueue(store, actor, body: JobInput):
    with operation_span(
        "job.enqueue",
        kind=SpanKind.PRODUCER,
        attributes={"job.type": body.kind if body.kind in JOB_TYPES else "unknown"},
    ):
        return _enqueue(store, actor, body)


def _enqueue(store, actor, body):
    actor.require("analyst")
    if body.kind not in {"event_poll", "assessment", "agent_task", "agent_plan"}:
        raise ValueError("Job type is not registered.")
    key = hashlib.sha256(
        f"{actor.tenant_id}|{body.kind}|{body.idempotency_key}".encode()
    ).hexdigest()
    id = f"job-{key}"
    with tenant_transaction(store.engine, actor.tenant_id) as session:
        org = store.organisation(session, actor.tenant_id)
        existing = session.get(WorkRecord, (actor.tenant_id, id))
        if existing:
            if (
                existing.payload["input_sha256"]
                != hashlib.sha256(canonical(body.payload).encode()).hexdigest()
            ):
                raise ValueError("Job idempotency key was already used with different input.")
            return encode(existing)
        active_jobs = session.scalar(
            select(func.count())
            .select_from(WorkRecord)
            .where(
                WorkRecord.tenant_id == actor.tenant_id,
                WorkRecord.kind == "job",
                WorkRecord.status.in_(("pending", "running")),
            )
        )
        if active_jobs >= MAX_ACTIVE_JOBS_PER_TENANT:
            raise ValueError("Tenant has reached the active job limit.")
        record = add(
            session,
            actor.tenant_id,
            "job",
            "pending",
            {
                "job_type": body.kind,
                "input": body.payload,
                "input_sha256": hashlib.sha256(canonical(body.payload).encode()).hexdigest(),
                "attempts": 0,
                "retry_at": datetime.now(UTC).isoformat(),
                "deadline_at": (
                    datetime.now(UTC)
                    + timedelta(
                        seconds=int(
                            org.policy.get("job_timeout_seconds", DEFAULT_JOB_TIMEOUT_SECONDS)
                        )
                    )
                ).isoformat(),
                **trace_headers(),
            },
            id,
        )
        store.append(session, org, "job.enqueued", actor.subject, {"id": id, "kind": body.kind})
        return encode(record)


def _claim(store, tenant_id: str):
    now = datetime.now(UTC)
    with tenant_transaction(store.engine, tenant_id) as session:
        org = store.organisation(session, tenant_id)
        hourly_limit = int(org.policy.get("job_hourly_limit", DEFAULT_JOB_HOURLY_LIMIT))
        window = now.replace(minute=0, second=0, microsecond=0)
        budget_id = f"execution-budget-{window.strftime('%Y%m%d%H')}"
        budget_record = session.get(WorkRecord, (tenant_id, budget_id))
        query = (
            select(WorkRecord)
            .where(
                WorkRecord.tenant_id == tenant_id,
                WorkRecord.kind == "job",
                or_(WorkRecord.status == "pending", WorkRecord.status == "running"),
            )
            .order_by(WorkRecord.created_at, WorkRecord.id)
            .with_for_update(skip_locked=True)
        )
        for record in session.scalars(query):
            retry_at = datetime.fromisoformat(record.payload["retry_at"])
            lease_until = (
                datetime.fromisoformat(record.payload["lease_until"])
                if record.payload.get("lease_until")
                else None
            )
            if record.status == "running" and lease_until and lease_until > now:
                continue
            if record.status == "pending" and retry_at > now:
                continue
            if datetime.fromisoformat(record.payload["deadline_at"]) <= now:
                record.status = "failed"
                record.payload = {
                    **record.payload,
                    "lease_until": None,
                    "claim_id": None,
                    "error": "JobDeadlineExceeded",
                }
                store.append(
                    session,
                    org,
                    "job.failed",
                    "worker",
                    {
                        "id": record.id,
                        "attempt": record.payload["attempts"],
                        "reason": "deadline",
                    },
                )
                continue
            if record.payload["attempts"] >= MAX_ATTEMPTS:
                record.status = "failed"
                record.payload = {**record.payload, "lease_until": None, "claim_id": None}
                store.append(
                    session,
                    org,
                    "job.failed",
                    "worker",
                    {
                        "id": record.id,
                        "attempt": record.payload["attempts"],
                        "reason": "attempt_limit",
                    },
                )
                continue
            used = int(budget_record.payload["used"]) if budget_record else 0
            if used >= hourly_limit:
                return None
            if budget_record is None:
                budget_record = add(
                    session,
                    tenant_id,
                    "execution_budget",
                    "open",
                    {
                        "window_start": window.isoformat(),
                        "limit": hourly_limit,
                        "used": 0,
                    },
                    budget_id,
                )
            budget_record.payload = {**budget_record.payload, "used": used + 1}
            record.status = "running"
            record.payload = {
                **record.payload,
                "attempts": record.payload["attempts"] + 1,
                "lease_until": (now + LEASE).isoformat(),
                "claim_id": uuid4().hex,
            }
            return record.id, record.payload
    return None


def run_next(store, actor):
    actor.require("analyst")
    from substrata.platform.governance import expire_pending_approvals
    from substrata.platform.notifications import deliver_pending_confirmations

    expire_pending_approvals(store, actor)
    notification_result = deliver_pending_confirmations(store, actor)
    claimed = _claim(store, actor.tenant_id)
    if claimed is None:
        return (
            {"kind": "notification_delivery", **notification_result}
            if notification_result.get("attempted", 0)
            else None
        )
    job_id, payload = claimed
    job_type = payload["job_type"] if payload["job_type"] in JOB_TYPES else "unknown"
    started = time.perf_counter()
    with operation_span(
        "job.execute",
        kind=SpanKind.CONSUMER,
        parent=parent_context(payload.get("traceparent")),
        attributes={"job.type": job_type, "job.attempt": payload["attempts"]},
    ) as span:
        result = None
        try:
            deadline = datetime.fromisoformat(payload["deadline_at"])
            with job_deadline(deadline):
                result = _run_claimed(store, actor, job_id, payload, span)
            return result
        finally:
            ids = span.get_span_context()
            logging.getLogger("substrata.jobs").info(
                json.dumps(
                    {
                        "event": "job.execution",
                        "job_type": job_type,
                        "attempt": payload["attempts"],
                        "status": result["status"] if result else "error",
                        "trace_id": f"{ids.trace_id:032x}",
                        "span_id": f"{ids.span_id:016x}",
                        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                    },
                    separators=(",", ":"),
                )
            )


def _run_claimed(store, actor, job_id, payload, span):
    try:
        with tenant_transaction(store.engine, actor.tenant_id) as session:
            _require_claim(session, actor.tenant_id, job_id, payload)
        require_time()
        if payload["job_type"] == "event_poll":
            from substrata.platform.events import poll

            result = {"processed": poll(store, actor.tenant_id)}
        elif payload["job_type"] == "assessment":
            from substrata.platform.governance import save_assessment

            job_input = payload["input"]
            assessment = {
                **job_input["assessment"],
                "as_of": TypeAdapter(AwareDatetime).validate_python(
                    job_input["assessment"]["as_of"]
                ),
            }
            result = save_assessment(
                store,
                actor,
                **assessment,
                version=job_input["graph_version"],
                idempotency_key=job_id,
            )
        elif payload["job_type"] == "agent_task":
            from substrata.platform.agent_protocols import AGENT_TASK_TO_TOOL, execute_tool

            task = payload["input"]
            result = execute_tool(
                store,
                actor,
                AGENT_TASK_TO_TOOL[task["agent"]],
                task["arguments"],
                idempotency_key=job_id,
            )
        elif payload["job_type"] == "agent_plan":
            result = _run_agent_plan(store, actor, job_id, payload)
        else:
            raise ValueError("Persisted job type is not registered.")
        require_time()
    except LeaseLost:
        span.set_attribute("job.lease_lost", True)
        return _lost_claim(job_id, payload)
    except JobDeadlineExceeded:
        span.set_status(Status(StatusCode.ERROR))
        span.set_attribute("error.type", "JobDeadlineExceeded")
        with tenant_transaction(store.engine, actor.tenant_id) as session:
            org = store.organisation(session, actor.tenant_id)
            try:
                record = _require_claim(
                    session,
                    actor.tenant_id,
                    job_id,
                    payload,
                    check_deadline=False,
                )
            except LeaseLost:
                return _lost_claim(job_id, payload)
            record.status = "failed"
            record.payload = {
                **record.payload,
                "lease_until": None,
                "claim_id": None,
                "error": "JobDeadlineExceeded",
            }
            store.append(
                session,
                org,
                "job.failed",
                actor.subject,
                {"id": job_id, "attempt": payload["attempts"], "reason": "deadline"},
            )
        return {"id": job_id, "status": "failed", "attempt": payload["attempts"]}
    except Exception as error:
        span.set_status(Status(StatusCode.ERROR))
        span.set_attribute("error.type", type(error).__name__)
        now = datetime.now(UTC)
        attempts = payload["attempts"]
        failed = attempts >= MAX_ATTEMPTS
        retry_at = now + timedelta(seconds=RETRY[min(attempts - 1, len(RETRY) - 1)])
        with tenant_transaction(store.engine, actor.tenant_id) as session:
            org = store.organisation(session, actor.tenant_id)
            try:
                record = _require_claim(
                    session, actor.tenant_id, job_id, payload, check_deadline=False
                )
            except LeaseLost:
                span.set_attribute("job.lease_lost", True)
                return _lost_claim(job_id, payload)
            latest_payload = record.payload
            record.status = "failed" if failed else "pending"
            record.payload = {
                **latest_payload,
                "lease_until": None,
                "claim_id": None,
                "retry_at": retry_at.isoformat(),
                "error": type(error).__name__,
            }
            store.append(
                session,
                org,
                "job.failed" if failed else "job.retry_scheduled",
                actor.subject,
                {
                    "id": job_id,
                    "attempt": attempts,
                    "error_type": type(error).__name__,
                    "retry_at": retry_at.isoformat(),
                },
            )
        return {
            "id": job_id,
            "status": "failed" if failed else "retry_scheduled",
            "attempt": attempts,
        }
    with tenant_transaction(store.engine, actor.tenant_id) as session:
        org = store.organisation(session, actor.tenant_id)
        try:
            record = _require_claim(session, actor.tenant_id, job_id, payload, check_deadline=False)
        except LeaseLost:
            span.set_attribute("job.lease_lost", True)
            return _lost_claim(job_id, payload)
        paused = isinstance(result, dict) and result.get("status") == "paused"
        record.status = "paused" if paused else "succeeded"
        record.payload = {
            **record.payload,
            "result": result,
            "lease_until": None,
            "claim_id": None,
        }
        store.append(
            session,
            org,
            "agent_plan.paused" if paused else "job.completed",
            actor.subject,
            {
                "id": job_id,
                "attempt": payload["attempts"],
                "awaiting": result.get("awaiting") if paused else None,
            },
        )
        return encode(record)


def _run_agent_plan(store, actor, job_id, payload):
    """Run LangGraph, retaining the typed assessment/audit plan as an offline fallback."""
    if os.environ.get("SUBSTRATA_AGENT_ORCHESTRATOR", "langgraph") == "typed":
        return _run_typed_agent_plan(store, actor, job_id, payload)

    from substrata.platform.orchestration import build_risk_review_graph

    checkpoints = dict(payload.get("checkpoints", {}))

    def persist(step, result):
        checkpoints[step] = result
        with tenant_transaction(store.engine, actor.tenant_id) as session:
            org = store.organisation(session, actor.tenant_id)
            record = _require_claim(session, actor.tenant_id, job_id, payload)
            record.payload = {**record.payload, "checkpoints": checkpoints}
            store.append(
                session,
                org,
                "agent_plan.step_completed",
                actor.subject,
                {"id": job_id, "step": step, "result": result},
            )

    graph = build_risk_review_graph(store, actor, job_id, persist)
    result = graph.invoke(
        {
            "arguments": payload["input"]["arguments"],
            "checkpoints": checkpoints,
            "human_checkpoints": dict(payload.get("human_checkpoints", {})),
            "status": "running",
            "awaiting": None,
        }
    )
    return {
        "plan": "risk_review",
        "orchestrator": "langgraph",
        "status": result.get("status", "completed"),
        "awaiting": result.get("awaiting"),
        "checkpoints": result.get("checkpoints", checkpoints),
    }


def _run_typed_agent_plan(store, actor, job_id, payload):
    """Run the compatibility assessment/audit workflow without LangGraph."""
    from substrata.platform.agent_protocols import AssessmentArguments, execute_tool
    from substrata.platform.governance import save_assessment

    plan = payload["input"]
    arguments = AssessmentArguments.model_validate(plan["arguments"])
    checkpoints = dict(payload.get("checkpoints", {}))
    steps = (
        "cascade_caller.assessment",
        "compliance_audit.verification",
    )
    for step in steps:
        if step in checkpoints:
            continue
        with tenant_transaction(store.engine, actor.tenant_id) as session:
            _require_claim(session, actor.tenant_id, job_id, payload)
        if step == "cascade_caller.assessment":
            assessment = save_assessment(
                store,
                actor,
                arguments.source_id,
                arguments.severity,
                as_of=arguments.as_of,
                version=arguments.graph_version,
                max_depth=arguments.max_depth,
                idempotency_key=f"{job_id}-assessment",
            )
            checkpoint = {
                "assessment_id": assessment["id"],
                "status": assessment["status"],
                "graph_version": assessment["payload"]["report"]["graph_version"],
            }
        else:
            verification = execute_tool(store, actor, "audit.verify", {})
            checkpoint = {
                "valid": verification["valid"],
                "head": verification["head"],
                "count": verification["count"],
            }
        checkpoints[step] = checkpoint
        with tenant_transaction(store.engine, actor.tenant_id) as session:
            org = store.organisation(session, actor.tenant_id)
            record = _require_claim(session, actor.tenant_id, job_id, payload)
            record.payload = {**record.payload, "checkpoints": checkpoints}
            store.append(
                session,
                org,
                "agent_plan.step_completed",
                actor.subject,
                {"id": job_id, "step": step, "result": checkpoint},
            )
    return {
        "plan": "risk_review",
        "orchestrator": "typed_fallback",
        "status": "completed",
        "awaiting": None,
        "checkpoints": checkpoints,
    }


def resume_agent_plan(store, actor, job_id: str, body: AgentPlanResume):
    """Resume a paused LangGraph plan after a named human checkpoint."""
    actor.require("analyst")
    with tenant_transaction(store.engine, actor.tenant_id) as session:
        org = store.organisation(session, actor.tenant_id)
        record = session.get(WorkRecord, (actor.tenant_id, job_id))
        if record is None or record.kind != "job" or record.payload.get("job_type") != "agent_plan":
            raise ValueError("Risk-review job is unavailable.")
        awaiting = record.payload.get("result", {}).get("awaiting")
        if record.status != "paused" or awaiting != body.checkpoint:
            raise ValueError("Risk-review job is not waiting at that checkpoint.")
        if body.checkpoint == "approval":
            pending_ids = (
                record.payload.get("checkpoints", {}).get("approval", {}).get("action_ids", [])
            )
            current = (
                {
                    item.id: item.status
                    for item in session.scalars(
                        select(WorkRecord).where(
                            WorkRecord.tenant_id == actor.tenant_id,
                            WorkRecord.kind == "mitigation",
                            WorkRecord.id.in_(pending_ids),
                        )
                    )
                }
                if pending_ids
                else {}
            )
            if any(status == "pending" for status in current.values()):
                raise ValueError("Complete the named approval decision before resuming.")
        if body.checkpoint == "relationship_review":
            awaiting_ids = set(
                record.payload.get("checkpoints", {})
                .get("relationship_review", {})
                .get("relationship_ids", [])
            )
            current_links = {
                link.id: link.status for link in store.snapshot(actor.tenant_id).data.links
            }
            unresolved = sorted(
                link_id
                for link_id in awaiting_ids
                if current_links.get(link_id) in {None, "inferred"}
            )
            if unresolved:
                raise ValueError(
                    "Confirm, reject, expire or supersede every inferred relationship "
                    "before resuming."
                )
        human = dict(record.payload.get("human_checkpoints", {}))
        human[body.checkpoint] = {
            "actor": actor.subject,
            "reason": body.reason,
            "recorded_at": datetime.now(UTC).isoformat(),
            "graph_version": org.version,
        }
        next_input = record.payload["input"]
        next_checkpoints = dict(record.payload.get("checkpoints", {}))
        if body.checkpoint == "relationship_review":
            next_input = {
                **next_input,
                "arguments": {**next_input["arguments"], "graph_version": org.version},
            }
            next_checkpoints = {}
        timeout = int(org.policy.get("job_timeout_seconds", DEFAULT_JOB_TIMEOUT_SECONDS))
        record.status = "pending"
        record.payload = {
            **record.payload,
            "input": next_input,
            "checkpoints": next_checkpoints,
            "human_checkpoints": human,
            "retry_at": datetime.now(UTC).isoformat(),
            "deadline_at": (datetime.now(UTC) + timedelta(seconds=timeout)).isoformat(),
            "lease_until": None,
            "claim_id": None,
            "result": None,
        }
        store.append(
            session,
            org,
            "agent_plan.resumed",
            actor.subject,
            {"id": job_id, "checkpoint": body.checkpoint, "reason": body.reason},
        )
        return encode(record)


def jobs(store, tenant_id: str, limit=50):
    return list_records(store, tenant_id, kind="job", limit=min(max(limit, 1), 200))


def get_agent_plan_job(store, actor, task_id):
    """Read one tenant-owned A2A risk-review job using its client task ID."""
    actor.require("viewer")
    TypeAdapter(Identifier).validate_python(task_id)
    key = hashlib.sha256(f"{actor.tenant_id}|agent_plan|{task_id}".encode()).hexdigest()
    with tenant_transaction(store.engine, actor.tenant_id) as session:
        record = session.get(WorkRecord, (actor.tenant_id, f"job-{key}"))
        if record is None:
            return None
        return encode(record)
