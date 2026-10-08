"""Assumption-based mitigation ranking; every payload is simulated only."""

import math

from pydantic import BaseModel

from substrata.cascade import CascadeResult

POLICY_VERSION = "synthetic-policy-v1"


class Mitigation(BaseModel):
    kind: str
    title: str
    cost: float
    duration_days: float
    risk: float
    rank_score: float
    policy: str
    rationale: str
    payload: dict


def policy_evaluate(kind: str, cost: float, result: CascadeResult, spend_limit: float) -> str:
    allowed = {
        "buffer_buy",
        "plant_reallocation",
        "expedite",
        "alternate_qualification",
        "safety_stock",
    }
    if (
        kind not in allowed
        or not math.isfinite(cost)
        or cost < 0
        or not math.isfinite(spend_limit)
        or spend_limit < 0
    ):
        return "block"
    if (
        not result.impacts
        or result.truncated
        or any(i.status == "incomplete" for i in result.impacts)
    ):
        return "block"
    if not any(i.exposure_window for i in result.impacts):
        return "block"
    if cost > spend_limit or kind in {"alternate_qualification", "plant_reallocation"}:
        return "review"
    return "record_preview"


def rank_mitigations(result: CascadeResult, spend_limit: float = 10000) -> list[Mitigation]:
    options = [
        ("buffer_buy", "Draft a buffer purchase", 15000, 7, 0.35),
        ("plant_reallocation", "Review stock reallocation", 4000, 2, 0.30),
        ("expedite", "Preview expedited in-transit supply", 6000, 4, 0.25),
        ("alternate_qualification", "Start alternate-source qualification", 25000, 90, 0.10),
        ("safety_stock", "Preview a safety-stock increase", 8000, 12, 0.40),
    ]
    ranked = []
    for kind, title, cost, days, risk in options:
        decision = policy_evaluate(kind, cost, result, spend_limit)
        score = round(0.4 * cost / 25000 + 0.35 * days / 90 + 0.25 * risk, 4)
        ranked.append(
            Mitigation(
                kind=kind,
                title=title,
                cost=cost,
                duration_days=days,
                risk=risk,
                rank_score=score,
                policy=decision,
                rationale=f"Synthetic estimate: USD {cost:,.0f}, {days:g} days, "
                f"risk score {risk:g}. Capacity, availability and qualification require review; "
                "no real transaction is sent.",
                payload={
                    "external_execution": "simulated_only",
                    "currency": "USD",
                    "cost_assumption": True,
                    "kind": kind,
                    "components": sorted({i.component_id for i in result.impacts}),
                    "plants": sorted({i.plant_id for i in result.impacts}),
                    "policy_version": POLICY_VERSION,
                },
            )
        )
    return sorted(ranked, key=lambda action: (action.rank_score, action.kind))
