"""Tenant policies and frozen-input approvals; execution is dry-run by default."""

import hashlib
import os
from datetime import UTC, datetime, timedelta
from typing import Literal, Protocol

from pydantic import Field, model_validator
from sqlalchemy import select

from substrata.platform.auth import Principal
from substrata.platform.cascade import assess
from substrata.platform.database import tenant_transaction
from substrata.platform.domain import Contract, Measure
from substrata.platform.models import WorkRecord
from substrata.platform.records import add, encode, require_record
from substrata.platform.store import Conflict
from substrata.seed import canonical


class Policy(Contract):
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    spend_limit: Measure
    auto_approve_limit: Measure
    approval_sla: Measure
    llm_daily_budget: Measure | None = None
    job_hourly_limit: int = Field(default=100, ge=1, le=10000)
    job_timeout_seconds: int = Field(default=120, ge=5, le=3600)
    approver_roles: set[Literal["approver", "admin"]] = {"approver", "admin"}
    require_separate_approver: bool = True
    allowed_kinds: set[str] = {
        "buffer_buy",
        "expedite",
        "plant_reallocation",
        "alternate_qualification",
        "safety_stock",
    }

    @model_validator(mode="after")
    def units(self):
        if self.spend_limit.unit != self.currency or self.auto_approve_limit.unit != self.currency:
            raise ValueError("Policy limits must use the policy currency.")
        if self.auto_approve_limit.value > self.spend_limit.value:
            raise ValueError("Automatic approval limit cannot exceed the spending limit.")
        if self.approval_sla.unit != "hour" or not 0 < self.approval_sla.value <= 168:
            raise ValueError("Approval SLA must be between zero and 168 hours.")
        if not self.approver_roles:
            raise ValueError("At least one authenticated approver role is required.")
        if self.llm_daily_budget is not None and self.llm_daily_budget.unit != "USD":
            raise ValueError("Live inference budget must be expressed in USD.")
        return self


class ProposalInput(Contract):
    assessment_id: str
    kind: str = Field(min_length=1, max_length=48)
    title: str = Field(min_length=1, max_length=256)
    cost: Measure
    duration: Measure
    rationale: str = Field(min_length=1, max_length=2000)
    adapter: Literal["preview", "sap"] = "preview"


class ExecutionAdapter(Protocol):
    def execute(self, payload: dict, *, idempotency_key: str) -> dict: ...


class DryRunAdapter:
    def execute(self, payload, *, idempotency_key):
        return {
            "mode": "dry_run",
            "idempotency_key": idempotency_key,
            "payload": payload,
            "message": "No external transaction was sent.",
        }


def configure_policy(store, actor: Principal, policy: Policy):
    actor.require("admin")
    with tenant_transaction(store.engine, actor.tenant_id) as session:
        org = store.organisation(session, actor.tenant_id)
        org.policy = policy.model_dump(mode="json")
        store.append(session, org, "policy.changed", actor.subject, {"policy": org.policy})
        return org.policy


def save_assessment(
    store,
    actor,
    source_id,
    severity,
    *,
    as_of,
    version=None,
    max_depth=8,
    idempotency_key=None,
):
    actor.require("analyst")
    snapshot = store.snapshot(actor.tenant_id, version=version)

    def path_finder(source, target, depth, paths, work):
        return store.paths(
            actor.tenant_id,
            source,
            target,
            version=snapshot.version,
            traversal_as_of=as_of,
            max_depth=depth,
            max_paths=paths,
            budget=work,
        )

    report = assess(
        snapshot,
        source_id,
        severity,
        as_of=as_of,
        max_depth=max_depth,
        path_finder=path_finder,
    )
    with tenant_transaction(store.engine, actor.tenant_id) as session:
        org = store.organisation(session, actor.tenant_id)
        status = (
            "incomplete"
            if report["truncated"] or any(i["status"] == "incomplete" for i in report["impacts"])
            else "complete"
        )
        record_id = (
            "assessment-"
            + hashlib.sha256(f"{actor.tenant_id}|{idempotency_key}".encode()).hexdigest()
            if idempotency_key
            else None
        )
        if record_id:
            existing = session.get(WorkRecord, (actor.tenant_id, record_id))
            if existing is not None:
                return encode(existing)
        record = add(
            session,
            actor.tenant_id,
            "assessment",
            status,
            {
                "report": report,
                "requester": actor.subject,
                "input_snapshot": snapshot.model_dump(mode="json"),
            },
            record_id,
        )
        store.append(
            session,
            org,
            "assessment.completed",
            actor.subject,
            {"id": record.id, "graph_sha256": snapshot.sha256, "status": status},
        )
        return encode(record)


def expire_pending_approvals(store, actor: Principal, *, limit=500):
    """Apply expired approval deadlines and publish one tenant notification per action."""
    actor.require("analyst")
    now = datetime.now(UTC)
    expired_ids = []
    with tenant_transaction(store.engine, actor.tenant_id) as session:
        due_before_lock = list(
            session.scalars(
                select(WorkRecord.id)
                .where(
                    WorkRecord.tenant_id == actor.tenant_id,
                    WorkRecord.kind == "mitigation",
                    WorkRecord.status == "pending",
                    WorkRecord.payload["expires_at"].as_string() <= now.isoformat(),
                )
                .order_by(WorkRecord.created_at, WorkRecord.id)
                .limit(min(max(limit, 1), 500))
            )
        )
        if not due_before_lock:
            return []
        org = store.organisation(session, actor.tenant_id)
        pending = session.scalars(
            select(WorkRecord)
            .where(
                WorkRecord.tenant_id == actor.tenant_id,
                WorkRecord.id.in_(due_before_lock),
                WorkRecord.kind == "mitigation",
                WorkRecord.status == "pending",
                WorkRecord.payload["expires_at"].as_string() <= now.isoformat(),
            )
            .order_by(WorkRecord.created_at, WorkRecord.id)
            .limit(min(max(limit, 1), 500))
            .with_for_update(skip_locked=True)
        )
        notifications = list(
            session.scalars(
                select(WorkRecord)
                .where(
                    WorkRecord.tenant_id == actor.tenant_id,
                    WorkRecord.kind == "notification",
                    WorkRecord.status == "pending",
                )
                .limit(1000)
            )
        )
        for action in pending:
            action.status = "expired"
            action.payload = {
                **action.payload,
                "approval": {
                    "actor": actor.subject,
                    "reason": "Approval SLA expired before a decision.",
                    "decided_at": now.isoformat(),
                },
            }
            for notification in notifications:
                if notification.payload.get("action_id") == action.id:
                    notification.status = "expired"
            notification_id = "approval-expired-" + hashlib.sha256(action.id.encode()).hexdigest()
            if session.get(WorkRecord, (actor.tenant_id, notification_id)) is None:
                add(
                    session,
                    actor.tenant_id,
                    "notification",
                    "pending",
                    {
                        "type": "approval_expired",
                        "action_id": action.id,
                        "title": action.payload["title"],
                        "channel": "portal",
                    },
                    notification_id,
                )
            store.append(
                session,
                org,
                "approval.expired",
                actor.subject,
                {"id": action.id, "reason": "approval_sla_elapsed"},
            )
            expired_ids.append(action.id)
    return expired_ids


def propose(store, actor: Principal, body: ProposalInput, *, idempotency_key: str | None = None):
    actor.require("analyst")
    request_sha256 = hashlib.sha256(canonical(body.model_dump(mode="json")).encode()).hexdigest()
    action_id = None
    if idempotency_key is not None:
        if not isinstance(idempotency_key, str) or not 1 <= len(idempotency_key) <= 96:
            raise ValueError("Mitigation idempotency key is invalid.")
        action_id = (
            "mitigation-"
            + hashlib.sha256(f"{actor.tenant_id}|{idempotency_key}".encode()).hexdigest()
        )
    with tenant_transaction(store.engine, actor.tenant_id) as session:
        org = store.organisation(session, actor.tenant_id)
        if action_id is not None:
            existing = session.get(WorkRecord, (actor.tenant_id, action_id))
            if existing is not None:
                if existing.payload.get("idempotency_sha256") != request_sha256:
                    raise Conflict(
                        "Mitigation idempotency key was already used with different input."
                    )
                return encode(existing)
        assessment = require_record(session, actor.tenant_id, body.assessment_id, "assessment")
        report = assessment.payload["report"]
        reasons = []
        policy = Policy.model_validate(org.policy) if org.policy else None
        if policy is None:
            reasons.append("Tenant policy has not been configured.")
        if assessment.status != "complete" or not report["impacts"]:
            reasons.append("A complete assessment with affected inventory is required.")
        if org.version != report["graph_version"]:
            reasons.append("Assessment graph is stale.")
        if body.duration.unit != "day":
            reasons.append("Action duration must be expressed in days.")
        if policy and (
            body.kind not in policy.allowed_kinds
            or body.cost.unit != policy.currency
            or body.cost.value > policy.spend_limit.value
        ):
            reasons.append("Action kind, currency or spending exceeds tenant policy.")
        status = (
            "blocked"
            if reasons
            else "approved"
            if (
                body.cost.value <= policy.auto_approve_limit.value
                and body.kind not in {"alternate_qualification", "plant_reallocation"}
            )
            else "pending"
        )
        payload = {
            **body.model_dump(mode="json"),
            "requester": actor.subject,
            "graph_version": report["graph_version"],
            "graph_sha256": report["graph_sha256"],
            "evidence_sha256": report["evidence_sha256"],
            "calculation_sha256": hashlib.sha256(canonical(report).encode()).hexdigest(),
            "formula_version": report["formula_version"],
            "policy_sha256": hashlib.sha256(canonical(org.policy).encode()).hexdigest(),
            "expires_at": (
                datetime.now(UTC) + timedelta(hours=policy.approval_sla.value if policy else 1)
            ).isoformat(),
            "assigned_to": None,
            "blocked_reasons": reasons,
            "idempotency_sha256": request_sha256 if action_id is not None else None,
            "approval": {
                "actor": "Tenant policy",
                "reason": "Within configured automatic threshold.",
            }
            if status == "approved"
            else None,
        }
        action = add(session, actor.tenant_id, "mitigation", status, payload, action_id)
        store.append(
            session,
            org,
            "mitigation.proposed",
            actor.subject,
            {"id": action.id, "status": status, "cost": payload["cost"], "reasons": reasons},
        )
        if status == "pending":
            add(
                session,
                actor.tenant_id,
                "notification",
                "pending",
                {
                    "type": "approval_needed",
                    "action_id": action.id,
                    "title": body.title,
                    "due_at": payload["expires_at"],
                    "channel": "portal",
                },
            )
            from substrata.platform.notifications import queue_approval_email_notifications

            queue_approval_email_notifications(
                store, session, actor.tenant_id, actor.subject, action
            )
        return encode(action)


def decide(store, actor: Principal, id: str, decision: str, reason: str):
    actor.require("approver")
    if decision not in {"approved", "rejected"} or not reason.strip():
        raise ValueError("An approval/rejection decision and reason are required.")
    expired = False
    with tenant_transaction(store.engine, actor.tenant_id) as session:
        org = store.organisation(session, actor.tenant_id)
        action = require_record(session, actor.tenant_id, id, "mitigation")
        policy = Policy.model_validate(org.policy)
        if not actor.roles & policy.approver_roles:
            raise ValueError("Authenticated role is outside the tenant's approval policy.")
        if action.status != "pending":
            raise Conflict("Action is no longer awaiting a decision.")
        if policy.require_separate_approver and action.payload["requester"] == actor.subject:
            raise ValueError(
                "Policy requires a different person to approve the requester’s action."
            )
        if action.payload.get("assigned_to") not in {None, actor.subject}:
            raise ValueError("Action is delegated to a different approver.")
        stale = (
            org.version != action.payload["graph_version"]
            or action.payload["policy_sha256"]
            != hashlib.sha256(canonical(org.policy).encode()).hexdigest()
        )
        assessment = require_record(
            session, actor.tenant_id, action.payload["assessment_id"], "assessment"
        )
        stale = (
            stale
            or action.payload.get("calculation_sha256")
            != hashlib.sha256(canonical(assessment.payload["report"]).encode()).hexdigest()
        )
        expired = stale or datetime.now(UTC) >= datetime.fromisoformat(action.payload["expires_at"])
        action.status = "expired" if expired else decision
        action.payload = {
            **action.payload,
            "review_status": "returned_for_review"
            if expired or decision == "rejected"
            else "complete",
            "approval": {
                "actor": actor.subject,
                "roles": sorted(actor.roles),
                "reason": "Inputs/policy changed or SLA expired." if expired else reason,
                "decided_at": datetime.now(UTC).isoformat(),
            },
        }
        store.append(
            session,
            org,
            "approval." + action.status,
            actor.subject,
            {"id": id, "decision": action.status, "approval": action.payload["approval"]},
        )
        result = encode(action)
    if expired:
        raise Conflict("Approval expired; reassess and draft a new action.")
    return result


def delegate(store, actor: Principal, id: str, subject: str, reason: str):
    actor.require("approver")
    if not subject.strip() or len(subject) > 256 or not reason.strip():
        raise ValueError("Delegation requires an identity-provider subject and reason.")
    expired = False
    with tenant_transaction(store.engine, actor.tenant_id) as session:
        org = store.organisation(session, actor.tenant_id)
        action = require_record(session, actor.tenant_id, id, "mitigation")
        policy = Policy.model_validate(org.policy)
        if not actor.roles & policy.approver_roles:
            raise ValueError("Authenticated role is outside the tenant's approval policy.")
        if action.status != "pending":
            raise Conflict("Only pending approvals may be delegated.")
        if (
            action.payload.get("assigned_to") not in {None, actor.subject}
            and "admin" not in actor.roles
        ):
            raise ValueError("Only the assigned approver or an administrator can delegate.")
        now = datetime.now(UTC)
        expired = (
            org.version != action.payload["graph_version"]
            or action.payload["policy_sha256"]
            != hashlib.sha256(canonical(org.policy).encode()).hexdigest()
            or now >= datetime.fromisoformat(action.payload["expires_at"])
        )
        if expired:
            action.status = "expired"
            action.payload = {
                **action.payload,
                "approval": {
                    "actor": actor.subject,
                    "roles": sorted(actor.roles),
                    "reason": "Inputs/policy changed or SLA expired.",
                    "decided_at": now.isoformat(),
                },
            }
            store.append(
                session,
                org,
                "approval.expired",
                actor.subject,
                {"id": id, "decision": "expired", "approval": action.payload["approval"]},
            )
        else:
            action.payload = {**action.payload, "assigned_to": subject}
            store.append(
                session,
                org,
                "approval.delegated",
                actor.subject,
                {"id": id, "assigned_to": subject, "reason": reason},
            )
            add(
                session,
                actor.tenant_id,
                "notification",
                "pending",
                {
                    "type": "approval_delegated",
                    "action_id": id,
                    "subject": subject,
                    "channel": "portal",
                },
            )
        result = encode(action)
    if expired:
        raise Conflict("Approval expired; reassess and draft a new action.")
    return result


def execute(store, actor: Principal, id: str, *, adapter: ExecutionAdapter | None = None):
    actor.require("approver")
    with tenant_transaction(store.engine, actor.tenant_id) as session:
        org = store.organisation(session, actor.tenant_id)
        action = require_record(session, actor.tenant_id, id, "mitigation")
        if action.status in {"executed", "dry_run"}:
            return encode(action)
        if action.status != "approved" or org.version != action.payload["graph_version"]:
            raise Conflict("Execution requires an approved action and unchanged graph inputs.")
        if (
            action.payload["policy_sha256"]
            != hashlib.sha256(canonical(org.policy).encode()).hexdigest()
        ):
            raise Conflict("Policy changed after approval; submit a new action.")
        assessment = require_record(
            session, actor.tenant_id, action.payload["assessment_id"], "assessment"
        )
        if (
            action.payload.get("calculation_sha256")
            != hashlib.sha256(canonical(assessment.payload["report"]).encode()).hexdigest()
        ):
            raise Conflict("Calculation changed after approval; submit a new action.")
        live = os.environ.get("SUBSTRATA_SAP_WRITES_ENABLED") == "true"
        if live:
            if action.payload["approval"]["actor"] == "Tenant policy":
                raise ValueError("Real SAP writes require explicit human approval.")
            if os.environ.get("SUBSTRATA_ENV", "development") == "development":
                raise ValueError("Real SAP writes are prohibited in development.")
            if adapter is None or action.payload["adapter"] != "sap":
                raise ValueError("Explicit approved SAP adapter configuration is required.")
        else:
            adapter = DryRunAdapter()
        result = adapter.execute(action.payload, idempotency_key=f"{actor.tenant_id}:{id}")
        action.payload = {**action.payload, "execution": result}
        action.status = "executed" if live else "dry_run"
        store.append(
            session, org, "action." + action.status, actor.subject, {"id": id, "result": result}
        )
        return encode(action)
