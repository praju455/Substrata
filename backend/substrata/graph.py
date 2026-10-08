"""Versioned database projection and bounded deterministic dependency traversal."""

import math
from datetime import datetime
from typing import Protocol

import networkx as nx
from pydantic import BaseModel, Field
from sqlalchemy import Engine, select

from substrata.database import transaction
from substrata.models import EdgeEvidence, EvidenceRecord, GraphEdge, GraphNode, SourceSnapshot
from substrata.seed import AS_OF, canonical


class GraphSnapshot(BaseModel):
    version: int
    as_of: datetime
    nodes: list[dict]
    edges: list[dict]


class EvidencePath(BaseModel):
    nodes: list[str]
    edge_ids: list[str]
    confidence: float


class PathResult(BaseModel):
    paths: list[EvidencePath] = Field(default_factory=list)
    confidence: float = 0
    truncated: bool = False


class GraphStore(Protocol):
    def snapshot(self, version: int = 1, as_of: datetime = AS_OF) -> GraphSnapshot: ...
    def paths(self, source: str, target: str, version: int = 1) -> PathResult: ...
    def propose_edge(self, values: dict) -> str: ...


class NetworkXGraphStore:
    def __init__(self, engine: Engine):
        self.engine = engine

    def snapshot(self, version: int = 1, as_of: datetime = AS_OF) -> GraphSnapshot:
        with transaction(self.engine) as session:
            nodes = [
                {
                    "id": n.id,
                    "name": n.name,
                    "node_type": n.node_type,
                    "attributes": n.attributes.model_dump(mode="json"),
                    "synthetic": n.synthetic,
                }
                for n in session.scalars(
                    select(GraphNode)
                    .where(GraphNode.graph_version == version)
                    .order_by(GraphNode.id)
                )
            ]
            citations = {}
            rows = session.execute(
                select(EdgeEvidence, EvidenceRecord, SourceSnapshot)
                .join(EvidenceRecord, EdgeEvidence.evidence_id == EvidenceRecord.id)
                .join(SourceSnapshot, EvidenceRecord.source_snapshot_id == SourceSnapshot.id)
                .where(EdgeEvidence.graph_version == version)
                .order_by(EdgeEvidence.evidence_id)
            )
            for link, evidence, source in rows:
                citations.setdefault(link.edge_id, []).append(
                    {
                        "id": evidence.id,
                        "quote": evidence.claim,
                        "stance": link.stance,
                        "source_uri": source.source_uri,
                        "source_kind": source.source_kind,
                        "sha256": source.content_sha256,
                    }
                )
            edges = [
                {
                    "id": e.id,
                    "source": e.from_node_id,
                    "target": e.to_node_id,
                    "edge_type": e.edge_type,
                    "status": e.status,
                    "confidence": e.confidence,
                    "valid_from": e.valid_from.isoformat(),
                    "valid_to": e.valid_to.isoformat() if e.valid_to else None,
                    "evidence": citations.get(e.id, []),
                }
                for e in session.scalars(
                    select(GraphEdge)
                    .where(GraphEdge.graph_version == version)
                    .order_by(GraphEdge.id)
                )
            ]
        return GraphSnapshot(version=version, as_of=as_of, nodes=nodes, edges=edges)

    def paths(self, source: str, target: str, version: int = 1) -> PathResult:
        return dependency_paths(project(self.snapshot(version)), source, target)

    def propose_edge(self, values: dict) -> str:
        if values.get("status") != "inferred" or not values.get("primary_evidence_id"):
            raise ValueError("Only evidence-backed inferred edges may be proposed.")
        with transaction(self.engine) as session:
            existing = session.get(GraphEdge, (values["id"], values["graph_version"]))
            if existing is not None:
                if (existing.from_node_id, existing.to_node_id, existing.edge_type) != (
                    values["from_node_id"],
                    values["to_node_id"],
                    values["edge_type"],
                ):
                    raise ValueError("Edge identity conflict.")
                return existing.id
            session.add(GraphEdge(**values))
        return values["id"]


def project(snapshot: GraphSnapshot) -> nx.MultiDiGraph:
    """Reverse ownership/location for event propagation; exclude rejected/expired links."""
    graph = nx.MultiDiGraph()
    graph.add_nodes_from((n["id"], n) for n in snapshot.nodes)
    for edge in snapshot.edges:
        if edge["status"] not in {"declared", "inferred", "confirmed"}:
            continue
        if datetime.fromisoformat(edge["valid_from"]) > snapshot.as_of:
            continue
        if edge["valid_to"] and datetime.fromisoformat(edge["valid_to"]) <= snapshot.as_of:
            continue
        source, target = edge["source"], edge["target"]
        if edge["edge_type"] in {"OWNED_BY", "LOCATED_IN"}:
            source, target = target, source
        graph.add_edge(source, target, key=edge["id"], **edge)
    return graph


def dependency_paths(
    graph: nx.MultiDiGraph,
    source: str,
    target: str,
    max_depth: int = 8,
    max_paths: int = 128,
    budget: int = 10000,
) -> PathResult:
    """Cycle-safe simple paths with explicit depth, work and result limits."""
    result = PathResult()
    if source not in graph or target not in graph:
        return result
    if min(max_depth, max_paths, budget) < 1:
        raise ValueError("Traversal limits must be positive.")
    stack = [(source, [source], [], 1.0)]
    work = 0
    while stack:
        node, visited, edges, confidence = stack.pop()
        work += 1
        if work > budget:
            result.truncated = True
            break
        if node == target:
            result.paths.append(EvidencePath(nodes=visited, edge_ids=edges, confidence=confidence))
            if len(result.paths) >= max_paths:
                result.truncated = bool(stack)
                break
            continue
        if len(edges) >= max_depth:
            result.truncated |= any(n not in visited for n in graph.successors(node))
            continue
        outgoing = sorted(graph.out_edges(node, keys=True, data=True), key=lambda e: (e[1], e[2]))
        for _, next_node, edge_id, data in reversed(outgoing):
            if next_node not in visited:
                stack.append(
                    (
                        next_node,
                        [*visited, next_node],
                        [*edges, edge_id],
                        confidence * data["confidence"],
                    )
                )
    result.confidence = 1 - math.prod(1 - path.confidence for path in result.paths)
    return result


def fingerprint(snapshot: GraphSnapshot) -> str:
    import hashlib

    return hashlib.sha256(canonical(snapshot.model_dump(mode="json")).encode()).hexdigest()


def shared_dependencies(snapshot: GraphSnapshot, tier1_ids: list[str]) -> list[dict]:
    graph = project(snapshot)
    result = []
    for node in snapshot.nodes:
        if node["node_type"] != "SupplierSite" or node["id"] in tier1_ids:
            continue
        reachable = [
            site for site in sorted(tier1_ids) if dependency_paths(graph, node["id"], site).paths
        ]
        if len(reachable) >= 3:
            result.append({"node_id": node["id"], "name": node["name"], "supplier_ids": reachable})
    return result
