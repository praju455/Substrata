"""Tenant policies and frozen-input approvals; execution is dry-run by default."""

import hashlib
import os
from datetime import UTC, datetime, timedelta
from typing import Literal, Protocol

from pydantic import Field, model_validator

from substrata.platform.auth import Principal
from substrata.platform.cascade import assess
from substrata.platform.database import tenant_transaction
from substrata.platform.domain import Contract, Measure
from substrata.platform.records import add, encode, require_record
from substrata.platform.store import Conflict
from substrata.seed import canonical


class Policy(Contract):
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    spend_limit: Measure
    auto_approve_limit: Measure
    approval_sla: Measure
    llm_daily_budget: Measure | None = None
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


def save_assessment(store, actor, source_id, severity, *, as_of, version=None, max_depth=8):
    actor.require("analyst")
    snapshot = store.snapshot(actor.tenant_id, version=version)
    report = assess(snapshot, source_id, severity, as_of=as_of, max_depth=max_depth)
    with tenant_transaction(store.engine, actor.tenant_id) as session:
        org = store.organisation(session, actor.tenant_id)
        status = (
            "incomplete"
            if report["truncated"] or any(i["status"] == "incomplete" for i in report["impacts"])
            else "complete"
        )
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
        )
        store.append(
            session,
            org,
            "assessment.completed",
            actor.subject,
            {"id": record.id, "graph_sha256": snapshot.sha256, "status": status},
        )
        return encode(record)


def propose(store, actor: Principal, body: ProposalInput):
    actor.require("analyst")
    with tenant_transaction(store.engine, actor.tenant_id) as session:
        org = store.organisation(session, actor.tenant_id)
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
            "policy_sha256": hashlib.sha256(canonical(org.policy).encode()).hexdigest(),
            "expires_at": (
                datetime.now(UTC) + timedelta(hours=policy.approval_sla.value if policy else 1)
            ).isoformat(),
            "assigned_to": None,
            "blocked_reasons": reasons,
            "approval": {
                "actor": "Tenant policy",
                "reason": "Within configured automatic threshold.",
            }
            if status == "approved"
            else None,
        }
        action = add(session, actor.tenant_id, "mitigation", status, payload)
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
        expired = stale or datetime.now(UTC) >= datetime.fromisoformat(action.payload["expires_at"])
        action.status = "expired" if expired else decision
        action.payload = {
            **action.payload,
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
    with tenant_transaction(store.engine, actor.tenant_id) as session:
        org = store.organisation(session, actor.tenant_id)
        action = require_record(session, actor.tenant_id, id, "mitigation")
        if action.status != "pending":
            raise Conflict("Only pending approvals may be delegated.")
        if (
            action.payload.get("assigned_to") not in {None, actor.subject}
            and "admin" not in actor.roles
        ):
            raise ValueError("Only the assigned approver or an administrator can delegate.")
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
        return encode(action)


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
