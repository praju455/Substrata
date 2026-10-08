"""Frozen input fingerprints and transactional named approval decisions."""

import hashlib
from datetime import UTC, datetime

from sqlalchemy import Engine, inspect, select

from substrata.actions import POLICY_VERSION
from substrata.audit import append_audit
from substrata.cascade import FORMULA_VERSION
from substrata.database import transaction
from substrata.erp_models import (
    BomItem,
    Dataset,
    LeadTime,
    PlantStock,
    PurchasingDocument,
    VendorMaster,
)
from substrata.graph import NetworkXGraphStore, fingerprint
from substrata.seed import DATASET, canonical
from substrata.workflow_models import ActionProposal, ApprovalDecision, ApprovalRequest, Scenario


def row_data(row) -> dict:
    values = {
        attribute.key: getattr(row, attribute.key) for attribute in inspect(type(row)).column_attrs
    }
    return {
        key: value.isoformat() if isinstance(value, datetime) else value
        for key, value in values.items()
    }


def current_input_hashes(engine: Engine, spend_limit: float = 10000) -> dict:
    graph_hash = fingerprint(NetworkXGraphStore(engine).snapshot())
    with transaction(engine) as session:
        inputs = {}
        for model in (Dataset, VendorMaster, BomItem, PlantStock, LeadTime, PurchasingDocument):
            rows = [row_data(row) for row in session.scalars(select(model))]
            inputs[model.__tablename__] = sorted(rows, key=canonical)
    return {
        "formula_version": FORMULA_VERSION,
        "policy_version": POLICY_VERSION,
        "spend_limit": spend_limit,
        "graph_sha256": graph_hash,
        "erp_sha256": hashlib.sha256(canonical(inputs).encode()).hexdigest(),
    }


def decide_action(
    engine: Engine,
    action_id: str,
    actor: str,
    role: str,
    decision: str,
    reason: str,
    current_hashes: dict,
    now: datetime | None = None,
) -> dict:
    actor, reason = actor.strip(), reason.strip()
    if not actor or not reason or role not in {"procurement_approver", "planning_approver"}:
        raise ValueError("A named approver, permitted demo role and reason are required.")
    if decision not in {"approved", "rejected"}:
        raise ValueError("Decision must be approved or rejected.")
    now = now or datetime.now(UTC)
    expired = False
    with transaction(engine) as session:
        action = session.get(ActionProposal, action_id)
        queue = session.get(ApprovalRequest, action_id)
        if action is None or queue is None or queue.status != "pending":
            raise ValueError("Approval is missing or already decided.")
        scenario = session.get(Scenario, action.scenario_id)
        stale = (
            scenario.snapshot["input_hashes"] != current_hashes
            or queue.snapshot_sha256
            != hashlib.sha256(canonical(scenario.snapshot).encode()).hexdigest()
            or scenario.snapshot["policy_version"] != POLICY_VERSION
            or scenario.snapshot["dataset_version"] != DATASET
        )
        if stale or now > queue.expires_at:
            queue.status, action.status = "expired", "expired"
            append_audit(
                session,
                "approval_expired",
                "Policy",
                {
                    "action_id": action_id,
                    "reason": "Input snapshot changed" if stale else "Approval timed out",
                },
            )
            expired = True
        else:
            session.add(
                ApprovalDecision(
                    action_id=action_id,
                    actor=actor,
                    role=role,
                    decision=decision,
                    reason=reason,
                    decided_at=now,
                )
            )
            queue.status, action.status = (
                decision,
                "simulated" if decision == "approved" else "rejected",
            )
            scenario.status = "AUDITED" if decision == "approved" else "REJECTED"
            append_audit(
                session,
                decision,
                actor,
                {
                    "action_id": action_id,
                    "scenario_id": scenario.id,
                    "role": role,
                    "reason": reason,
                    "data_sources": scenario.snapshot["input_hashes"],
                    "payload": action.payload,
                    "external_execution": "simulated_only",
                },
            )
            if decision == "approved":
                for other in session.scalars(
                    select(ApprovalRequest)
                    .join(ActionProposal)
                    .where(
                        ActionProposal.scenario_id == scenario.id,
                        ApprovalRequest.action_id != action_id,
                        ApprovalRequest.status == "pending",
                    )
                ):
                    other.status = "superseded"
                    session.get(ActionProposal, other.action_id).status = "superseded"
                append_audit(
                    session,
                    "logged",
                    "Audit",
                    {
                        "action_id": action_id,
                        "result": "Simulated payload recorded. No external execution.",
                    },
                )
    if expired:
        raise ValueError(
            "Approval expired because its snapshot or validity changed. Replay a new scenario."
        )
    return {"action_id": action_id, "decision": decision, "external_execution": "simulated_only"}
