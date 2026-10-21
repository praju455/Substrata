"""LangGraph orchestration for the governed, resumable risk-review workflow."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from substrata.platform import agent_protocols, governance
from substrata.platform.agent_protocols import AssessmentArguments
from substrata.platform.database import tenant_transaction
from substrata.platform.models import Organisation
from substrata.platform.records import list_records

RiskReviewStep = Literal[
    "evidence_mapping",
    "event_sensing",
    "relationship_review",
    "deterministic_impact",
    "mitigation_drafting",
    "policy_checks",
    "approval",
    "audit",
]


class RiskReviewState(TypedDict, total=False):
    arguments: dict
    checkpoints: dict[str, dict]
    human_checkpoints: dict[str, dict]
    status: Literal["running", "paused", "completed"]
    awaiting: str | None


PersistCheckpoint = Callable[[RiskReviewStep, dict], None]


def _active_links(snapshot, source_id: str):
    return [
        link
        for link in snapshot.data.links
        if link.status not in {"rejected", "expired", "superseded"}
        and (link.source == source_id or link.target == source_id)
    ]


def build_risk_review_graph(store, actor, job_id: str, persist: PersistCheckpoint):
    """Build the explicit agent/tool workflow around deterministic business services."""

    def completed(state: RiskReviewState, step: RiskReviewStep):
        return state.get("checkpoints", {}).get(step)

    def save(state: RiskReviewState, step: RiskReviewStep, result: dict):
        checkpoints = dict(state.get("checkpoints", {}))
        checkpoints[step] = result
        persist(step, result)
        return {"checkpoints": checkpoints}

    def evidence_mapping(state: RiskReviewState):
        if completed(state, "evidence_mapping"):
            return {}
        arguments = AssessmentArguments.model_validate(state["arguments"])
        snapshot = store.snapshot(actor.tenant_id, version=arguments.graph_version)
        links = _active_links(snapshot, arguments.source_id)
        result = {
            "status": "complete" if links else "incomplete",
            "source_id": arguments.source_id,
            "relationship_ids": [link.id for link in links],
            "citation_count": sum(len(link.evidence) for link in links),
            "graph_version": snapshot.version,
            "graph_sha256": snapshot.sha256,
        }
        return save(state, "evidence_mapping", result)

    def event_sensing(state: RiskReviewState):
        if completed(state, "event_sensing"):
            return {}
        arguments = AssessmentArguments.model_validate(state["arguments"])
        snapshot = store.snapshot(actor.tenant_id, version=arguments.graph_version)
        entity = next(
            (item for item in snapshot.data.entities if item.id == arguments.source_id), None
        )
        if entity is None:
            raise ValueError("The disruption source is absent from the pinned graph revision.")
        matching = [
            record
            for record in list_records(store, actor.tenant_id, kind="event", limit=200)
            if record["payload"].get("source_id") == entity.id
            or record["payload"].get("resolution", {}).get("entity_id") == entity.id
        ]
        result = {
            "status": "resolved",
            "entity_id": entity.id,
            "entity_name": entity.name,
            "entity_kind": entity.kind,
            "event_ids": [record["id"] for record in matching],
        }
        return save(state, "event_sensing", result)

    def relationship_review(state: RiskReviewState):
        existing = completed(state, "relationship_review")
        if existing and existing.get("status") != "awaiting_human":
            return {}
        arguments = AssessmentArguments.model_validate(state["arguments"])
        snapshot = store.snapshot(actor.tenant_id, version=arguments.graph_version)
        inferred = [
            link.id
            for link in _active_links(snapshot, arguments.source_id)
            if link.status == "inferred"
        ]
        human = state.get("human_checkpoints", {}).get("relationship_review")
        if inferred and not human:
            result = {
                "status": "awaiting_human",
                "relationship_ids": inferred,
                "message": "Review inferred relationships before deterministic assessment.",
            }
            update = save(state, "relationship_review", result)
            return {**update, "status": "paused", "awaiting": "relationship_review"}
        result = {
            "status": "reviewed",
            "relationship_ids": inferred,
            "human_checkpoint": human,
        }
        update = save(state, "relationship_review", result)
        return {**update, "status": "running", "awaiting": None}

    def after_relationship_review(state: RiskReviewState):
        return END if state.get("status") == "paused" else "deterministic_impact"

    def deterministic_impact(state: RiskReviewState):
        if completed(state, "deterministic_impact"):
            return {}
        arguments = AssessmentArguments.model_validate(state["arguments"])
        assessment = governance.save_assessment(
            store,
            actor,
            arguments.source_id,
            arguments.severity,
            as_of=arguments.as_of,
            version=arguments.graph_version,
            max_depth=arguments.max_depth,
            idempotency_key=f"{job_id}-assessment",
        )
        report = assessment["payload"]["report"]
        result = {
            "assessment_id": assessment["id"],
            "status": assessment["status"],
            "graph_version": report["graph_version"],
            "graph_sha256": report["graph_sha256"],
            "formula_version": report["formula_version"],
            "impact_count": len(report["impacts"]),
            "truncated": report["truncated"],
        }
        return save(state, "deterministic_impact", result)

    def mitigation_drafting(state: RiskReviewState):
        if completed(state, "mitigation_drafting"):
            return {}
        impact = state["checkpoints"]["deterministic_impact"]
        actions = [
            record
            for record in list_records(store, actor.tenant_id, kind="mitigation", limit=200)
            if record["payload"].get("assessment_id") == impact["assessment_id"]
        ]
        result = {
            "status": "prepared",
            "assessment_id": impact["assessment_id"],
            "action_ids": [record["id"] for record in actions],
            "options": [
                "buffer_buy",
                "alternate_qualification",
                "expedite_route",
                "plant_reallocation",
            ],
            "simulated_only": True,
        }
        return save(state, "mitigation_drafting", result)

    def policy_checks(state: RiskReviewState):
        if completed(state, "policy_checks"):
            return {}
        with tenant_transaction(store.engine, actor.tenant_id) as session:
            organisation = session.get(Organisation, actor.tenant_id)
            policy = organisation.policy if organisation else {}
        actions = state["checkpoints"]["mitigation_drafting"]["action_ids"]
        result = {
            "status": "complete" if policy else "incomplete",
            "configured": bool(policy),
            "action_ids": actions,
            "external_execution": "simulated_only",
        }
        return save(state, "policy_checks", result)

    def approval(state: RiskReviewState):
        existing = completed(state, "approval")
        if existing and existing.get("status") not in {"awaiting_human", "pending"}:
            return {}
        action_ids = set(state["checkpoints"]["mitigation_drafting"]["action_ids"])
        actions = [
            record
            for record in list_records(store, actor.tenant_id, kind="mitigation", limit=200)
            if record["id"] in action_ids
        ]
        pending = [record["id"] for record in actions if record["status"] == "pending"]
        if pending:
            result = {
                "status": "awaiting_human",
                "action_ids": pending,
                "message": "A named approver must approve or reject each pending action.",
            }
            update = save(state, "approval", result)
            return {**update, "status": "paused", "awaiting": "approval"}
        result = {
            "status": "complete" if actions else "not_requested",
            "actions": [{"id": record["id"], "status": record["status"]} for record in actions],
        }
        update = save(state, "approval", result)
        return {**update, "status": "running", "awaiting": None}

    def after_approval(state: RiskReviewState):
        return END if state.get("status") == "paused" else "audit"

    def audit(state: RiskReviewState):
        if completed(state, "audit"):
            return {"status": "completed", "awaiting": None}
        verification = agent_protocols.execute_tool(store, actor, "audit.verify", {})
        result = {
            "valid": verification["valid"],
            "head": verification["head"],
            "count": verification["count"],
        }
        update = save(state, "audit", result)
        return {**update, "status": "completed", "awaiting": None}

    graph = StateGraph(RiskReviewState)
    graph.add_node("evidence_mapping", evidence_mapping)
    graph.add_node("event_sensing", event_sensing)
    graph.add_node("relationship_review", relationship_review)
    graph.add_node("deterministic_impact", deterministic_impact)
    graph.add_node("mitigation_drafting", mitigation_drafting)
    graph.add_node("policy_checks", policy_checks)
    graph.add_node("approval", approval)
    graph.add_node("audit", audit)
    graph.add_edge(START, "evidence_mapping")
    graph.add_edge("evidence_mapping", "event_sensing")
    graph.add_edge("event_sensing", "relationship_review")
    graph.add_conditional_edges("relationship_review", after_relationship_review)
    graph.add_edge("deterministic_impact", "mitigation_drafting")
    graph.add_edge("mitigation_drafting", "policy_checks")
    graph.add_edge("policy_checks", "approval")
    graph.add_conditional_edges("approval", after_approval)
    graph.add_edge("audit", END)
    return graph.compile()
