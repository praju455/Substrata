"""Evidence extraction cannot promote a relationship directly to confirmed truth."""

import json
import random
import time
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy import Engine, select

from substrata.agent_models import AgentRun, ConfirmationRequest, ConfirmationResponse, ToolCall
from substrata.database import transaction
from substrata.graph import NetworkXGraphStore
from substrata.llm import PROMPT_VERSION, Extraction, LLMClient, MockLLMClient, client_status
from substrata.models import EvidenceRecord, GraphEdge, SourceSnapshot
from substrata.seed import AS_OF, canonical


def map_evidence(engine: Engine, client: LLMClient | None = None, threshold: float = 0.75) -> dict:
    if not 0 <= threshold <= 1:
        raise ValueError("Inference threshold must be between zero and one.")
    client = client or MockLLMClient()
    snapshot = NetworkXGraphStore(engine).snapshot()
    names = {n["name"]: n["id"] for n in snapshot.nodes if n["node_type"] == "SupplierSite"}
    with transaction(engine) as session:
        records = [
            {
                "id": evidence.id,
                "text": source.permitted_excerpt,
                "reliability": evidence.reliability,
                "entities": names,
            }
            for evidence, source in session.execute(
                select(EvidenceRecord, SourceSnapshot)
                .join(SourceSnapshot)
                .order_by(EvidenceRecord.id)
            )
        ]
    started = time.perf_counter()
    run_id = str(uuid4())
    try:
        # Heuristic retrieval: exact known site names; co-location alone never proposes an edge.
        candidates = [r for r in records if sum(name in r["text"] for name in names) >= 2]
        extraction = Extraction.model_validate(
            client.generate_structured(
                task=PROMPT_VERSION, schema=Extraction.model_json_schema(), evidence=candidates
            )
        )
        by_id = {r["id"]: r for r in records}
        by_node = {n["id"]: n for n in snapshot.nodes}
        prepared = []
        for link in extraction.links:
            record = by_id.get(link.evidence_id)
            if record is None or link.quote not in record["text"]:
                raise ValueError("Extraction quote is not present in cited evidence.")
            source, target = by_node.get(link.from_id), by_node.get(link.to_id)
            if (
                not source
                or not target
                or source["node_type"] != "SupplierSite"
                or target["node_type"] != "SupplierSite"
            ):
                raise ValueError("Extraction endpoints must be known supplier sites.")
            expected = f"{source['name']} is owned by {target['name']}."
            if link.quote != expected or source["id"] == target["id"]:
                raise ValueError("Quote does not support these exact ownership endpoints.")
            confidence = round(0.8 * (record["reliability"] or 0) + 0.2, 3)
            prepared.append(
                (
                    link,
                    confidence,
                    {
                        "id": f"owned_by_{link.from_id}_{link.to_id}",
                        "graph_version": 1,
                        "from_node_id": link.from_id,
                        "to_node_id": link.to_id,
                        "from_node_type": "SupplierSite",
                        "to_node_type": "SupplierSite",
                        "edge_type": "OWNED_BY",
                        "status": "inferred",
                        "confidence": confidence,
                        "primary_evidence_id": link.evidence_id,
                        "valid_from": AS_OF.isoformat(),
                    },
                )
            )
        output = {
            "inferred": [],
            "confirmation_requests": [],
            "skipped": [],
            "run_id": run_id,
            "provider": client.provider,
            "model": client.model,
            "llm_attempts": client_status(client)["last_attempts"],
        }
        with transaction(engine) as session:
            for link, confidence, values in prepared:
                if session.get(GraphEdge, (values["id"], 1)) is not None:
                    output["skipped"].append(values["id"])
                    continue
                if confidence >= threshold:
                    session.add(GraphEdge(**{**values, "valid_from": AS_OF}))
                    output["inferred"].append(values["id"])
                else:
                    request_id = f"confirm_{values['id']}"
                    if session.get(ConfirmationRequest, request_id) is None:
                        session.add(
                            ConfirmationRequest(
                                id=request_id,
                                edge_id=values["id"],
                                graph_version=1,
                                evidence_id=link.evidence_id,
                                confidence=confidence,
                                quote=link.quote,
                                candidate=values,
                            )
                        )
                    output["confirmation_requests"].append(request_id)
            session.add(
                AgentRun(
                    id=run_id,
                    agent="Mapper",
                    status="completed",
                    provider=client.provider,
                    model=client.model,
                    prompt_version=PROMPT_VERSION,
                    latency_ms=(time.perf_counter() - started) * 1000,
                    schema_valid=True,
                    output={**output, "extraction": extraction.model_dump()},
                )
            )
            session.flush()
            session.add(
                ToolCall(
                    id=str(uuid4()),
                    agent_run_id=run_id,
                    tool="evidence.extract",
                    summary={
                        "candidate_records": len(candidates),
                        "extracted_links": len(prepared),
                        "threshold": threshold,
                    },
                )
            )
        return output
    except Exception as exc:
        with transaction(engine) as session:
            session.add(
                AgentRun(
                    id=run_id,
                    agent="Mapper",
                    status="failed",
                    provider=client.provider,
                    model=client.model,
                    prompt_version=PROMPT_VERSION,
                    latency_ms=(time.perf_counter() - started) * 1000,
                    schema_valid=False,
                    output={
                        "error_type": type(exc).__name__,
                        "llm_attempts": client_status(client)["last_attempts"],
                    },
                )
            )
        raise


def simulate_replies(
    engine: Engine, truth_path: Path, noise: float = 0, seed: int = 42
) -> list[dict]:
    """Only this simulated adapter (and evaluation) may read hidden ground truth."""
    if not 0 <= noise <= 1:
        raise ValueError("Reply noise must be between zero and one.")
    truth = json.loads(truth_path.read_text(encoding="utf-8"))
    true_edges = {(e["from_node_id"], e["to_node_id"], e["edge_type"]) for e in truth["edges"]}
    rng = random.Random(seed)
    outcomes = []
    with transaction(engine) as session:
        for request in session.scalars(
            select(ConfirmationRequest)
            .where(ConfirmationRequest.status == "pending")
            .order_by(ConfirmationRequest.id)
        ):
            values = request.candidate
            correct = (
                values["from_node_id"],
                values["to_node_id"],
                values["edge_type"],
            ) in true_edges
            if rng.random() < noise:
                correct = not correct
            decision = "confirmed" if correct else "rejected"
            session.add(
                ConfirmationResponse(
                    request_id=request.id,
                    decision=decision,
                    responder="Synthetic supplier simulator",
                    responded_at=AS_OF + timedelta(hours=1),
                    rationale=f"Simulated response; noise={noise}; seed={seed}. "
                    "No real supplier contacted.",
                )
            )
            session.flush()
            graph_edge = session.get(GraphEdge, (request.edge_id, request.graph_version))
            if graph_edge is None:
                graph_edge = GraphEdge(**{**values, "valid_from": AS_OF})
                session.add(graph_edge)
                session.flush()
            graph_edge.status = decision
            graph_edge.last_verified = AS_OF + timedelta(hours=1)
            request.status = decision
            outcomes.append(
                {
                    "request_id": request.id,
                    "edge_id": request.edge_id,
                    "decision": decision,
                    "simulated": True,
                }
            )
    return json.loads(canonical(outcomes))
