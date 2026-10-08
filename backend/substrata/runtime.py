"""One local state machine coordinates bounded tools and persisted agent events."""

import hashlib
import json
import math
import threading
from datetime import UTC, datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from uuid import uuid4

from pydantic import AwareDatetime, BaseModel, Field
from sqlalchemy import Engine, func, select

from substrata.actions import POLICY_VERSION, rank_mitigations
from substrata.agent_models import ConfirmationRequest, EvaluationRun
from substrata.audit import append_audit, records_in, verify_chain
from substrata.cascade import cascade
from substrata.database import transaction
from substrata.erp_models import Dataset, VendorMaster
from substrata.governance import current_input_hashes, decide_action, row_data
from substrata.graph import NetworkXGraphStore, shared_dependencies
from substrata.llm import PROMPT_VERSION, LLMClient, MockLLMClient, client_status
from substrata.mapper import map_evidence, simulate_replies
from substrata.seed import DATASET, canonical, seed_database
from substrata.workflow_models import (
    ActionProposal,
    ApprovalRequest,
    DemoState,
    EventEntityMatch,
    EventRecord,
    ImpactResult,
    Scenario,
    StreamEvent,
)


class ReplayEvent(BaseModel):
    id: str = Field(min_length=1, max_length=48)
    event_type: str = Field(min_length=1, max_length=48)
    observed_at: AwareDatetime
    title: str = Field(min_length=1, max_length=256)
    entity: str = Field(min_length=1, max_length=256)
    severity: float = Field(ge=0, le=1, allow_inf_nan=False)
    source_id: str
    description: str
    synthetic: bool


class Runtime:
    """Single-process demo runtime; mutations serialize and survive page reloads."""

    def __init__(
        self,
        engine: Engine,
        data_dir: Path,
        client: LLMClient | None = None,
        threshold: float = 0.75,
        spend_limit: float = 10000,
    ):
        if not 0 <= threshold <= 1 or not math.isfinite(spend_limit) or spend_limit < 0:
            raise ValueError("Invalid inference threshold or spend-limit configuration.")
        self.engine, self.data_dir = engine, data_dir
        self.client = client or MockLLMClient()
        self.threshold, self.spend_limit = threshold, spend_limit
        self.lock = threading.RLock()
        self.active = False
        self.task = None
        with transaction(engine) as session:
            if session.get(Dataset, DATASET) is None:
                raise ValueError("Run python scripts/dev.py seed before using the demo.")
            if session.get(DemoState, "current") is None:
                session.add(DemoState(id="current", generation=str(uuid4())))

    def input_hashes(self):
        return {
            **current_input_hashes(self.engine, self.spend_limit),
            "event_file_sha256": hashlib.sha256(
                (self.data_dir / "events.json").read_bytes()
            ).hexdigest(),
        }

    def ensure_chain(self):
        with transaction(self.engine) as session:
            if not verify_chain(records_in(session))["valid"]:
                raise ValueError(
                    "Audit chain is invalid; decisions are blocked. Reset the synthetic demo."
                )

    def publish(self, event_type: str, payload: dict, audit: bool = True):
        with transaction(self.engine) as session:
            session.add(
                StreamEvent(event_type=event_type, payload=payload, timestamp=datetime.now(UTC))
            )
            if audit:
                append_audit(session, event_type, "Demo agents", payload)

    def map(self):
        with self.lock:
            self.ensure_chain()
            result = map_evidence(self.engine, self.client, self.threshold)
            self.publish(
                "mapped",
                {
                    **result,
                    "rationale": "Exact quoted ownership evidence; scores are uncalibrated.",
                },
            )
            return result

    def confirm(self, noise: float = 0):
        with self.lock:
            self.ensure_chain()
            replies = simulate_replies(self.engine, self.data_dir / "true_graph.json", noise=noise)
            self.publish(
                "supplier_replied", {"replies": replies, "external_execution": "simulated_only"}
            )
            return replies

    def reset(self):
        with self.lock:
            self.active = False
            fingerprint = seed_database(self.engine, self.data_dir)
            with transaction(self.engine) as session:
                session.add(DemoState(id="current", generation=str(uuid4())))
            self.publish("reset", {"fixture_sha256": fingerprint, "synthetic": True})
            return {"reset": True, "fixture_sha256": fingerprint}

    def event_candidates(self, event: dict):
        snapshot = NetworkXGraphStore(self.engine).snapshot()
        normalized = " ".join(event["entity"].casefold().split())
        exact = [n for n in snapshot.nodes if n["name"].casefold() == normalized]
        if len(exact) == 1:
            return [
                {
                    "node_id": exact[0]["id"],
                    "name": exact[0]["name"],
                    "score": 1.0,
                    "method": "exact_name",
                }
            ]
        ranked = [
            {
                "node_id": n["id"],
                "name": n["name"],
                "score": round(SequenceMatcher(None, normalized, n["name"].casefold()).ratio(), 3),
                "method": "ambiguous_name",
            }
            for n in snapshot.nodes
        ]
        return sorted(
            [r for r in ranked if r["score"] >= 0.25], key=lambda r: (-r["score"], r["node_id"])
        )[:3]

    def process_next(self):
        with self.lock:
            self.ensure_chain()
            events = [
                ReplayEvent.model_validate(e).model_dump(mode="json")
                for e in json.loads((self.data_dir / "events.json").read_text(encoding="utf-8"))
            ]
            if not all(e["synthetic"] for e in events):
                raise ValueError("Only synthetic replay events are accepted.")
            with transaction(self.engine) as session:
                seen = set(session.scalars(select(EventRecord.id)))
            event = next((e for e in events if e["id"] not in seen), None)
            if event is None:
                return None
            candidates = self.event_candidates(event)
            exact = len(candidates) == 1 and candidates[0]["method"] == "exact_name"
            with transaction(self.engine) as session:
                session.add(
                    EventRecord(
                        id=event["id"],
                        event_type=event["event_type"],
                        observed_at=datetime.fromisoformat(event["observed_at"]),
                        ingested_at=datetime.now(UTC),
                        status="MATCHED" if exact else "NEEDS_REVIEW",
                        payload=event,
                    )
                )
                session.flush()
                for candidate in candidates:
                    session.add(
                        EventEntityMatch(
                            event_id=event["id"],
                            node_id=candidate["node_id"],
                            score=candidate["score"],
                            method=candidate["method"],
                        )
                    )
            self.publish(
                "event_received",
                {
                    "event_id": event["id"],
                    "title": event["title"],
                    "severity": event["severity"],
                    "classification": "high"
                    if event["severity"] >= 0.75
                    else "medium"
                    if event["severity"] >= 0.4
                    else "low",
                    "synthetic": True,
                },
            )
            if not exact:
                self.publish(
                    "analyst_review_needed", {"event_id": event["id"], "candidates": candidates}
                )
                return {"event_id": event["id"], "status": "NEEDS_REVIEW"}
            return self.analyse(event, candidates[0]["node_id"])

    def analyse(self, event: dict, node_id: str):
        snapshot = NetworkXGraphStore(self.engine).snapshot()
        if node_id not in {n["id"] for n in snapshot.nodes}:
            raise ValueError("Unknown graph node.")
        self.publish("matched", {"event_id": event["id"], "node_id": node_id})
        report = cascade(self.engine, snapshot, node_id, event["severity"])
        hashes = self.input_hashes()
        frozen = {
            "input_hashes": hashes,
            "graph": snapshot.model_dump(mode="json"),
            "graph_version": snapshot.version,
            "dataset_version": DATASET,
            "inventory_snapshot_id": report.inventory_snapshot_id,
            "event_snapshot_id": event["id"],
            "event": event,
            "source_id": node_id,
            "formula_version": report.formula_version,
            "policy_version": POLICY_VERSION,
            "prompt_version": PROMPT_VERSION,
            "provider": self.client.provider,
            "model": self.client.model,
        }
        proposals = rank_mitigations(report, self.spend_limit) if report.impacts else []
        with transaction(self.engine) as session:
            run_number = session.scalar(select(func.count()).select_from(Scenario)) + 1
            scenario_id = f"scenario_{event['id']}_{run_number}"
            session.add(
                Scenario(id=scenario_id, event_id=event["id"], status="ANALYSING", snapshot=frozen)
            )
            session.flush()
            session.add(
                ImpactResult(scenario_id=scenario_id, payload=report.model_dump(mode="json"))
            )
            for proposal in proposals:
                action_id = f"{scenario_id}:{proposal.kind}"
                status = {
                    "review": "awaiting_approval",
                    "block": "blocked",
                    "record_preview": "preview_recorded",
                }[proposal.policy]
                session.add(
                    ActionProposal(
                        id=action_id,
                        scenario_id=scenario_id,
                        status=status,
                        **proposal.model_dump(),
                    )
                )
                session.flush()
                if proposal.policy == "review":
                    session.add(
                        ApprovalRequest(
                            action_id=action_id,
                            snapshot_sha256=hashlib.sha256(canonical(frozen).encode()).hexdigest(),
                            expires_at=datetime.now(UTC) + timedelta(hours=1),
                            status="pending",
                        )
                    )
            status = (
                "AWAITING_APPROVAL"
                if any(p.policy == "review" for p in proposals)
                else "INCOMPLETE"
                if any(i.status == "incomplete" for i in report.impacts)
                else "AUDITED"
            )
            session.get(Scenario, scenario_id).status = status
            session.get(EventRecord, event["id"]).status = "ANALYSED"
        self.publish(
            "cascade_result", {"scenario_id": scenario_id, "report": report.model_dump(mode="json")}
        )
        for proposal in proposals:
            self.publish("action_proposed", {"scenario_id": scenario_id, **proposal.model_dump()})
            if proposal.policy == "review":
                self.publish(
                    "approval_needed",
                    {
                        "action_id": f"{scenario_id}:{proposal.kind}",
                        "title": proposal.title,
                        "cost": proposal.cost,
                        "policy_version": POLICY_VERSION,
                    },
                )
        return {"scenario_id": scenario_id, "status": status}

    def resolve(self, event_id: str, node_id: str, actor: str, reason: str):
        with self.lock:
            self.ensure_chain()
            if not actor.strip() or not reason.strip():
                raise ValueError("A named analyst and reason are required.")
            if node_id not in {n["id"] for n in NetworkXGraphStore(self.engine).snapshot().nodes}:
                raise ValueError("Unknown graph node.")
            with transaction(self.engine) as session:
                event = session.get(EventRecord, event_id)
                if event is None or event.status != "NEEDS_REVIEW":
                    raise ValueError("Event is missing or no longer awaiting review.")
                payload = event.payload
                append_audit(
                    session,
                    "analyst_resolved",
                    actor,
                    {"event_id": event_id, "node_id": node_id, "reason": reason},
                )
            return self.analyse(payload, node_id)

    def refresh(self, scenario_id: str):
        with self.lock:
            self.ensure_chain()
            with transaction(self.engine) as session:
                scenario = session.get(Scenario, scenario_id)
                if scenario is None:
                    raise ValueError("Unknown scenario.")
                event, node_id = scenario.snapshot["event"], scenario.snapshot["source_id"]
                for queue in session.scalars(
                    select(ApprovalRequest)
                    .join(ActionProposal)
                    .where(
                        ActionProposal.scenario_id == scenario_id,
                        ApprovalRequest.status == "pending",
                    )
                ):
                    queue.status = "superseded"
                    session.get(ActionProposal, queue.action_id).status = "superseded"
                append_audit(
                    session, "scenario_refreshed", "Analyst", {"previous_scenario_id": scenario_id}
                )
            return self.analyse(event, node_id)

    def decide(self, action_id: str, values: dict):
        with self.lock:
            self.ensure_chain()
            result = decide_action(
                self.engine, action_id, current_hashes=self.input_hashes(), **values
            )
            self.publish(values["decision"], result, audit=False)
            if values["decision"] == "approved":
                self.publish(
                    "logged",
                    {"action_id": action_id, "external_execution": "simulated_only"},
                    audit=False,
                )
            return result

    def stream_batch(self, after: int):
        with self.lock, transaction(self.engine) as session:
            generation = session.get(DemoState, "current").generation
            rows = session.scalars(
                select(StreamEvent)
                .where(StreamEvent.id > after)
                .order_by(StreamEvent.id)
                .limit(200)
            )
            return generation, [row_data(row) for row in rows]

    def state(self):
        with self.lock:
            snapshot = NetworkXGraphStore(self.engine).snapshot()
            with transaction(self.engine) as session:
                tier1 = list(
                    session.scalars(select(VendorMaster.supplier_site_id).order_by(VendorMaster.id))
                )
                audits = records_in(session)
                scenarios = [
                    {
                        "id": s.id,
                        "event_id": s.event_id,
                        "status": s.status,
                        "versions": {
                            k: v for k, v in s.snapshot.items() if k not in {"graph", "event"}
                        },
                        "report": session.get(ImpactResult, s.id).payload,
                    }
                    for s in session.scalars(select(Scenario).order_by(Scenario.id))
                ]
                events = []
                for event in session.scalars(select(EventRecord).order_by(EventRecord.id)):
                    candidates = [
                        row_data(row)
                        for row in session.scalars(
                            select(EventEntityMatch)
                            .where(EventEntityMatch.event_id == event.id)
                            .order_by(EventEntityMatch.score.desc())
                        )
                    ]
                    events.append({**row_data(event), "candidates": candidates})
                return {
                    "generation": session.get(DemoState, "current").generation,
                    "synthetic": True,
                    "llm": client_status(self.client),
                    "replay": {"active": self.active, "processed": len(events), "total": 6},
                    "graph": snapshot.model_dump(mode="json"),
                    "tier1_ids": tier1,
                    "shared_dependencies": shared_dependencies(snapshot, tier1),
                    "scenarios": scenarios,
                    "events": events,
                    "actions": [
                        row_data(row)
                        for row in session.scalars(
                            select(ActionProposal).order_by(ActionProposal.rank_score)
                        )
                    ],
                    "confirmations": [
                        row_data(row)
                        for row in session.scalars(
                            select(ConfirmationRequest).order_by(ConfirmationRequest.id)
                        )
                    ],
                    "audit": verify_chain(audits),
                    "audit_events": audits,
                    "evaluation": [row_data(row) for row in session.scalars(select(EvaluationRun))],
                }
