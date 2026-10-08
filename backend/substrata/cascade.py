"""Runway arithmetic is deterministic, unit-checked and independent of any LLM."""

import math
from datetime import timedelta
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import Engine, select

from substrata.database import transaction
from substrata.erp_models import Dataset, LeadTime, PlantStock, PurchasingDocument
from substrata.graph import GraphSnapshot, dependency_paths, project
from substrata.seed import DATASET

FORMULA_VERSION = "runway-v1"


class Impact(BaseModel):
    component_id: str
    component_name: str
    plant_id: str
    plant_name: str
    status: Literal["complete", "incomplete", "no_demand"]
    reason: str | None = None
    unit: str
    on_hand: float | None = None
    in_transit: float | None = None
    daily_consumption: float | None = None
    cover_days: float | None = None
    requalification_days: float | None = None
    exposure_window: float | None = None
    priority: float | None = None
    path_confidence: float
    paths: list[list[str]]
    evidence_ids: list[str]
    truncated: bool = False


class CascadeResult(BaseModel):
    source_id: str
    graph_version: int
    dataset_version: str
    inventory_snapshot_id: str
    formula_version: str = FORMULA_VERSION
    severity: float
    impacts: list[Impact]
    truncated: bool = False


def runway(
    on_hand: float | None,
    in_transit: float | None,
    daily: float | None,
    requalification: float | None,
) -> tuple[str, float | None, float | None]:
    if any(value is None for value in (on_hand, in_transit, daily, requalification)):
        return "incomplete", None, None
    if any(
        not math.isfinite(value) or value < 0
        for value in (on_hand, in_transit, daily, requalification)
    ):
        raise ValueError("Runway inputs must be finite and nonnegative.")
    if daily == 0:
        return "no_demand", None, 0
    cover = (on_hand + in_transit) / daily
    return "complete", cover, max(0, requalification - cover)


def cascade(
    engine: Engine,
    snapshot: GraphSnapshot,
    source_id: str,
    severity: float,
    dataset_version: str = DATASET,
) -> CascadeResult:
    if not 0 <= severity <= 1:
        raise ValueError("Severity must be between zero and one.")
    graph = project(snapshot)
    nodes = {node["id"]: node for node in snapshot.nodes}
    evidence = {e["id"]: [c["id"] for c in e["evidence"]] for e in snapshot.edges}
    impacts = []
    seen = set()
    with transaction(engine) as session:
        dataset = session.get(Dataset, dataset_version)
        if dataset is None or dataset.graph_version != snapshot.version:
            raise ValueError("Dataset and graph snapshot do not agree.")
        for stock in session.scalars(
            select(PlantStock)
            .where(PlantStock.dataset_version == dataset_version)
            .order_by(PlantStock.component_id, PlantStock.plant_id)
        ):
            paths = dependency_paths(graph, source_id, stock.component_id)
            if not paths.paths:
                continue
            seen.add((stock.component_id, stock.plant_id))
            component, plant = nodes[stock.component_id], nodes[stock.plant_id]
            reason = None
            if (
                stock.graph_version != dataset.graph_version
                or stock.as_of != dataset.as_of
                or stock.inventory_snapshot_id != dataset.inventory_snapshot_id
            ):
                reason = "Inventory snapshot does not match the pinned dataset."
            if stock.unit != component["attributes"]["unit"]:
                reason = "Stock and component units differ."
            if not dependency_paths(graph, stock.component_id, stock.plant_id).paths:
                reason = "No where-used path links this component to the plant."
            lead = session.get(LeadTime, (dataset_version, stock.component_id))
            requalification = lead.requalification_days if lead else None
            in_transit = 0.0
            available = stock.on_hand
            for purchase in session.scalars(
                select(PurchasingDocument)
                .where(
                    PurchasingDocument.dataset_version == dataset_version,
                    PurchasingDocument.component_id == stock.component_id,
                    PurchasingDocument.plant_id == stock.plant_id,
                    PurchasingDocument.status == "in_transit",
                )
                .order_by(PurchasingDocument.expected_at)
            ):
                if purchase.unit != stock.unit or purchase.graph_version != dataset.graph_version:
                    reason = "In-transit units or graph version do not match."
                    continue
                if (
                    available is not None
                    and stock.daily_consumption
                    and (
                        dataset.as_of
                        <= purchase.expected_at
                        <= dataset.as_of + timedelta(days=available / stock.daily_consumption)
                    )
                ):
                    in_transit += purchase.quantity
                    available += purchase.quantity
            status, cover, exposure = runway(
                stock.on_hand, in_transit, stock.daily_consumption, requalification
            )
            if reason:
                status, cover, exposure = "incomplete", None, None
            if status == "incomplete" and reason is None:
                reason = "Stock, consumption or qualification time is missing."
            priority = (
                round(100 * severity * paths.confidence * exposure / max(requalification, 1), 2)
                if status == "complete"
                else (0 if status == "no_demand" else None)
            )
            impacts.append(
                Impact(
                    component_id=stock.component_id,
                    component_name=component["name"],
                    plant_id=stock.plant_id,
                    plant_name=plant["name"],
                    status=status,
                    reason=reason,
                    unit=stock.unit,
                    on_hand=stock.on_hand,
                    in_transit=in_transit,
                    daily_consumption=stock.daily_consumption,
                    cover_days=cover,
                    requalification_days=requalification,
                    exposure_window=exposure,
                    priority=priority,
                    path_confidence=paths.confidence,
                    paths=[p.nodes for p in paths.paths],
                    evidence_ids=sorted(
                        {c for p in paths.paths for e in p.edge_ids for c in evidence[e]}
                    ),
                    truncated=paths.truncated,
                )
            )
        for component in snapshot.nodes:
            if component["node_type"] != "Component":
                continue
            paths = dependency_paths(graph, source_id, component["id"])
            if not paths.paths:
                continue
            for plant in snapshot.nodes:
                if plant["node_type"] != "Plant" or (component["id"], plant["id"]) in seen:
                    continue
                if dependency_paths(graph, component["id"], plant["id"]).paths:
                    impacts.append(
                        Impact(
                            component_id=component["id"],
                            component_name=component["name"],
                            plant_id=plant["id"],
                            plant_name=plant["name"],
                            status="incomplete",
                            reason="Inventory row is missing.",
                            unit=component["attributes"]["unit"],
                            path_confidence=paths.confidence,
                            paths=[p.nodes for p in paths.paths],
                            evidence_ids=sorted(
                                {c for p in paths.paths for e in p.edge_ids for c in evidence[e]}
                            ),
                            truncated=paths.truncated,
                        )
                    )
        impacts.sort(key=lambda i: (i.component_id, i.plant_id))
        return CascadeResult(
            source_id=source_id,
            graph_version=snapshot.version,
            dataset_version=dataset_version,
            inventory_snapshot_id=dataset.inventory_snapshot_id,
            severity=severity,
            impacts=impacts,
            truncated=any(i.truncated for i in impacts),
        )
