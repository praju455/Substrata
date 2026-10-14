"""Deterministic, bounded propagation over tenant snapshots. No LLM dependencies."""

import math
from datetime import datetime

import networkx as nx

from substrata.cascade import runway
from substrata.graph import dependency_paths
from substrata.platform.domain import GraphData, Snapshot

FORMULA_VERSION = "platform-runway-v1"


def projection(data: GraphData, as_of: datetime):
    graph = nx.MultiDiGraph()
    graph.add_nodes_from(
        (entity.id, {"kind": entity.kind, "name": entity.name}) for entity in data.entities
    )
    for link in data.links:
        if link.status in {"rejected", "expired"} or link.valid_from > as_of:
            continue
        if link.valid_to is not None and link.valid_to <= as_of:
            continue
        source, target = link.source, link.target
        if link.type in {"DEPENDS_ON", "OWNED_BY", "LOCATED_IN"}:
            source, target = target, source
        graph.add_edge(source, target, key=link.id, confidence=link.confidence, status=link.status)
    return graph


def confidence_bounds(paths, links):
    """Fréchet/union bounds avoid treating overlapping paths as independent."""
    bounds = []
    for path in paths:
        weights = [links[id].confidence for id in path.edge_ids]
        bounds.append((max(0, sum(weights) - len(weights) + 1), min(weights, default=1)))
    return [max((low for low, _ in bounds), default=0), min(1, sum(high for _, high in bounds))]


def assess(
    snapshot: Snapshot,
    source_id: str,
    severity: float,
    *,
    as_of: datetime,
    max_depth: int = 8,
    max_paths: int = 128,
    budget: int = 10000,
):
    if not math.isfinite(severity) or not 0 <= severity <= 1:
        raise ValueError("Severity must be a finite number between zero and one.")
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("Assessment time must include a timezone.")
    if (
        max_depth < 1
        or max_depth > 32
        or max_paths < 1
        or max_paths > 512
        or not 1 <= budget <= 100000
    ):
        raise ValueError("Traversal limits exceed the supported bounds.")
    data = snapshot.data
    graph = projection(data, as_of)
    if source_id not in graph:
        raise ValueError("Event source must exist in the tenant graph.")
    entities = {e.id: e for e in data.entities}
    links = {e.id: e for e in data.links}
    impacts = []
    truncated = False
    for stock in data.inventory:
        paths = dependency_paths(graph, source_id, stock.material_id, max_depth, max_paths, budget)
        truncated |= paths.truncated
        if not paths.paths:
            continue
        material = entities[stock.material_id]
        plant = entities[stock.plant_id]
        qualification = material.measures.get("requalification_days")
        cover, exposure, reason = None, None, None
        available = stock.on_hand.value if stock.on_hand else None
        daily = stock.daily_consumption.value if stock.daily_consumption else None
        unit = stock.on_hand.unit if stock.on_hand else material.attributes.get("unit")
        eligible = []
        quantities = 0
        if stock.as_of > as_of:
            reason = "Inventory snapshot is later than the assessment time."
        if stock.daily_consumption and stock.daily_consumption.unit != f"{unit}/day":
            reason = "Consumption and stock units differ."
        if qualification and qualification.unit != "day":
            reason = "Qualification time must be expressed in days."
        if not dependency_paths(
            graph, stock.material_id, stock.plant_id, max_depth, max_paths, budget
        ).paths:
            reason = "No where-used path connects material to plant."
        # Roll stock forward to assessment time rather than counting historical stock as current.
        cursor = stock.as_of
        orders = sorted(
            (
                p
                for p in data.purchase_orders
                if p.material_id == stock.material_id
                and p.plant_id == stock.plant_id
                and p.status in {"open", "in_transit"}
                and p.expected_at >= stock.as_of
            ),
            key=lambda p: (p.expected_at, p.id),
        )
        for order in orders:
            if order.quantity.unit != unit:
                reason = "Purchase-order and inventory units differ."
                continue
            elapsed = max(0, (order.expected_at - cursor).total_seconds() / 86400)
            if available is None or daily is None or (daily and elapsed > available / daily):
                continue
            available -= daily * elapsed
            available += order.quantity.value
            quantities += order.quantity.value
            eligible.append(order.id)
            cursor = order.expected_at
        # Compute total uninterrupted cover from the stock snapshot, then elapsed cover.
        status, total_cover, _ = runway(
            stock.on_hand.value if stock.on_hand else None,
            quantities,
            daily,
            qualification.value if qualification else None,
        )
        elapsed = max(0, (as_of - stock.as_of).total_seconds() / 86400)
        if status == "complete":
            cover = max(0, total_cover - elapsed)
            exposure = max(0, qualification.value - cover)
        if reason:
            status, cover, exposure = "incomplete", None, None
        if status == "incomplete" and reason is None:
            reason = "Stock, demand or qualification time is missing."
        established = any(
            all(links[id].status in {"declared", "confirmed"} for id in path.edge_ids)
            for path in paths.paths
        )
        products = sorted(
            {bom.product_id for bom in data.boms if bom.material_id == stock.material_id}
        )
        revenue = []
        for product in products:
            rate = entities[product].measures.get("daily_revenue")
            if rate and rate.unit.endswith("/day") and exposure is not None:
                revenue.append(
                    {
                        "product_id": product,
                        "value_range": [
                            exposure * rate.value if established else 0,
                            exposure * rate.value,
                        ],
                        "unit": rate.unit.removesuffix("/day"),
                        "provenance": rate.provenance.model_dump(mode="json"),
                    }
                )
        citations = sorted(
            {
                c.document_id
                for path in paths.paths
                for id in path.edge_ids
                for c in links[id].evidence
            }
        )
        impacts.append(
            {
                "material_id": material.id,
                "material_name": material.name,
                "plant_id": plant.id,
                "plant_name": plant.name,
                "product_ids": products,
                "status": status,
                "reason": reason,
                "unit": unit,
                "cover_days": cover,
                "requalification_days": qualification.value if qualification else None,
                "exposure_days_range": [exposure if established else 0, exposure]
                if exposure is not None
                else None,
                "confidence_bounds": confidence_bounds(paths.paths, links),
                "confidence_label": "Uncalibrated evidence support; not disruption probability",
                "paths": [p.nodes for p in paths.paths],
                "evidence_ids": citations,
                "eligible_order_ids": eligible,
                "truncated": paths.truncated,
                "revenue": revenue,
                "provenance": {
                    "stock": stock.model_dump(mode="json"),
                    "qualification": qualification.model_dump(mode="json")
                    if qualification
                    else None,
                },
            }
        )
    # Missing inventory is explicitly incomplete instead of disappearing from exposure.
    existing = {(i["material_id"], i["plant_id"]) for i in impacts}
    for material in data.entities:
        if (
            material.kind != "Material"
            or not dependency_paths(
                graph, source_id, material.id, max_depth, max_paths, budget
            ).paths
        ):
            continue
        for plant in data.entities:
            if plant.kind != "Plant" or (material.id, plant.id) in existing:
                continue
            if dependency_paths(graph, material.id, plant.id, max_depth, max_paths, budget).paths:
                impacts.append(
                    {
                        "material_id": material.id,
                        "plant_id": plant.id,
                        "material_name": material.name,
                        "plant_name": plant.name,
                        "status": "incomplete",
                        "reason": "Inventory is missing.",
                        "cover_days": None,
                        "exposure_days_range": None,
                        "truncated": False,
                    }
                )
    shared = []
    suppliers = sorted(e.id for e in data.entities if e.kind == "Supplier")
    for entity in data.entities:
        reachable = [
            id
            for id in suppliers
            if id != entity.id
            and dependency_paths(graph, entity.id, id, max_depth, max_paths, budget).paths
        ]
        if len(reachable) >= 2:
            shared.append({"id": entity.id, "name": entity.name, "supplier_ids": reachable})
    concentration = []
    for material in (e for e in data.entities if e.kind == "Material"):
        shares = [
            link.measures["share"].value
            for link in data.links
            if link.type == "SUPPLIES"
            and link.target == material.id
            and link.id in {edge[2] for edge in graph.edges(keys=True)}
            and "share" in link.measures
        ]
        if shares:
            concentration.append(
                {
                    "material_id": material.id,
                    "hhi": sum(s * s for s in shares),
                    "known_share": sum(shares),
                    "complete": abs(sum(shares) - 1) < 1e-9,
                }
            )
    return {
        "tenant_id": snapshot.tenant_id,
        "graph_version": snapshot.version,
        "graph_sha256": snapshot.sha256,
        "source_id": source_id,
        "severity": severity,
        "as_of": as_of.isoformat(),
        "formula_version": FORMULA_VERSION,
        "impacts": sorted(impacts, key=lambda i: (i["material_id"], i["plant_id"])),
        "shared_dependencies": shared,
        "concentration": concentration,
        "truncated": truncated or any(i["truncated"] for i in impacts),
        "range_assumption": (
            "Full source interruption. Lower exposure is zero for paths relying on inferred links; "
            "upper exposure assumes those links hold. Revenue is gross at-risk revenue, "
            "not predicted loss."
        ),
    }
