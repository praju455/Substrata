"""Golden replay plus property-based monotonicity and uncertain shared paths."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from substrata.cascade import runway
from substrata.graph import EvidencePath
from substrata.platform.cascade import assess, confidence_bounds
from substrata.platform.domain import Citation, GraphData, Snapshot
from substrata.platform.quality import inventory_completeness
from substrata.platform.seeds import generate

AS_OF = datetime(2026, 10, 14, tzinfo=UTC)


def snapshot(industry="automotive"):
    return Snapshot(
        tenant_id="test",
        version=1,
        recorded_at=AS_OF,
        sha256="0" * 64,
        data=generate(industry, as_of=AS_OF),
    )


def test_golden_multi_industry_results():
    results = {}
    for industry in ("automotive", "pharma", "food"):
        report = assess(snapshot(industry), "upstream", 0.9, as_of=AS_OF)
        impact = report["impacts"][0]
        results[industry] = {
            "cover": impact["cover_days"],
            "qualification": impact["requalification_days"],
            "exposure": impact["exposure_days_range"],
            "shared": report["shared_dependencies"][0]["supplier_ids"],
        }
    golden = json.loads(
        (Path(__file__).parent / "fixtures/platform_cascade_golden.json").read_text()
    )
    for industry, expected in golden.items():
        assert results[industry]["cover"] == pytest.approx(expected["cover"])
        assert results[industry]["qualification"] == pytest.approx(expected["qualification"])
        assert results[industry]["exposure"] == pytest.approx(expected["exposure"])
        assert results[industry]["shared"] == expected["shared"]


@settings(max_examples=80)
@given(
    stock=st.floats(min_value=0, max_value=1e6),
    added=st.floats(min_value=0, max_value=1e6),
    daily=st.floats(min_value=1, max_value=1e5),
    days=st.floats(min_value=0, max_value=365),
)
def test_more_stock_never_increases_uncovered_days(stock, added, daily, days):
    _, cover, exposure = runway(stock, 0, daily, days)
    _, increased_cover, reduced = runway(stock + added, 0, daily, days)
    assert increased_cover >= cover
    assert reduced <= exposure


def test_historical_stock_is_rolled_forward_and_late_orders_cannot_bridge_gap():
    frozen = snapshot()
    report = assess(frozen, "upstream", 0.9, as_of=AS_OF + timedelta(days=5))
    assert report["impacts"][0]["cover_days"] == 13
    values = frozen.data.model_dump(mode="json")
    values["purchase_orders"][0]["expected_at"] = (AS_OF + timedelta(days=13)).isoformat()
    late = frozen.model_copy(update={"data": GraphData.model_validate(values)})
    impact = assess(late, "upstream", 0.9, as_of=AS_OF)["impacts"][0]
    assert impact["cover_days"] == 12
    assert impact["eligible_order_ids"] == []


def test_inferred_dependencies_report_exposure_range_and_missing_stock_is_incomplete():
    frozen = snapshot()
    values = frozen.data.model_dump(mode="json")
    for link in values["links"]:
        if link["type"] == "DEPENDS_ON":
            link["status"] = "inferred"
            link["confidence"] = 0.7
            link["evidence"] = [
                Citation(document_id="evidence", passage="claim", start=0, end=5).model_dump()
            ]
    data = GraphData.model_validate(values)
    uncertain = frozen.model_copy(update={"data": data})
    impact = assess(uncertain, "upstream", 0.9, as_of=AS_OF)["impacts"][0]
    assert impact["exposure_days_range"] == [0, 72]
    assert impact["revenue"][0]["value_range"] == [0, 3600000]
    no_stock = uncertain.model_copy(update={"data": data.model_copy(update={"inventory": []})})
    assert assess(no_stock, "upstream", 0.9, as_of=AS_OF)["impacts"][0]["status"] == "incomplete"
    quality = inventory_completeness(no_stock, as_of=AS_OF)["missing_row_count"]
    assert quality == 1


def test_inventory_completeness_distinguishes_absent_rows_and_missing_values():
    frozen = snapshot()
    complete = inventory_completeness(frozen, as_of=AS_OF)
    assert complete["expected_rows"] == 1
    assert complete["complete_rows"] == 1
    values = frozen.data.model_dump(mode="json")
    values["inventory"][0]["on_hand"] = None
    partial = frozen.model_copy(update={"data": GraphData.model_validate(values)})
    summary = inventory_completeness(partial, as_of=AS_OF)
    assert summary["missing_row_count"] == 0
    assert summary["missing_value_row_count"] == 1
    assert summary["incomplete_rows"][0]["missing_fields"] == ["on_hand"]


def test_overlapping_paths_have_conservative_bounds_and_cycles_terminate():
    frozen = snapshot()
    links = {link.id: link for link in frozen.data.links}
    links["dependency-0"] = links["dependency-0"].model_copy(update={"confidence": 0.5})
    paths = [EvidencePath(nodes=["a", "b"], edge_ids=["dependency-0"], confidence=0.5)] * 2
    assert confidence_bounds(paths, links) == [0.5, 1]
    with pytest.raises(ValueError):
        assess(frozen, "upstream", float("nan"), as_of=AS_OF)
    report = assess(frozen, "upstream", 0.9, as_of=AS_OF, max_depth=1)
    assert report["truncated"]


def one_route_snapshot(inferred_ids=()):
    values = snapshot().data.model_dump(mode="json")
    values["links"] = [
        link for link in values["links"] if link["id"] not in {"dependency-1", "dependency-2"}
    ]
    for link in values["links"]:
        if link["id"] in inferred_ids:
            link["status"] = "inferred"
            link["confidence"] = 0.4
            link["evidence"] = [
                Citation(
                    document_id=f"evidence-{link['id']}", passage="claim", start=0, end=5
                ).model_dump()
            ]
    return snapshot().model_copy(update={"data": GraphData.model_validate(values)})


def test_declared_routes_preserve_baseline_and_report_the_complete_plant_path():
    impact = assess(one_route_snapshot(), "upstream", 0.9, as_of=AS_OF)["impacts"][0]
    assert impact["cover_days"] == 18
    assert impact["exposure_days_range"] == [72, 72]
    assert impact["confidence_bounds"] == [1, 1]
    assert impact["paths"] == [["upstream", "supplier-0", "material", "plant"]]
    assert impact["revenue"][0]["value_range"] == [3600000, 3600000]
    assert impact["revenue"][0]["confidence_bounds"] == [1, 1]


@pytest.mark.parametrize(
    "inferred", [("used-plant",), ("used-product",), ("used-plant", "used-product")]
)
def test_downstream_inferred_routes_propagate_plant_and_product_support(inferred):
    impact = assess(one_route_snapshot(inferred), "upstream", 0.9, as_of=AS_OF)["impacts"][0]
    assert impact["exposure_days_range"] == ([0, 72] if "used-plant" in inferred else [72, 72])
    assert impact["confidence_bounds"] == pytest.approx(
        [0.4, 0.4] if "used-plant" in inferred else [1, 1]
    )
    revenue = impact["revenue"][0]
    assert revenue["value_range"] == [0, 3600000]
    assert revenue["confidence_bounds"][0] == pytest.approx(0 if len(inferred) == 2 else 0.4)
    assert revenue["confidence_bounds"][1] == pytest.approx(0.4)
    assert impact["evidence_ids"] == sorted(f"evidence-{id}" for id in inferred)
    assert "not disruption probability" in impact["confidence_label"]
    assert "not disruption probability" in revenue["confidence_label"]


def test_multiple_where_used_routes_union_support_without_assuming_independence():
    frozen = one_route_snapshot(("used-plant",))
    values = frozen.data.model_dump(mode="json")
    alternate = next(link.copy() for link in values["links"] if link["id"] == "used-plant")
    alternate.update(id="alternate-plant-route", confidence=0.2)
    values["links"].append(alternate)
    impact = assess(
        frozen.model_copy(update={"data": GraphData.model_validate(values)}),
        "upstream",
        0.9,
        as_of=AS_OF,
    )["impacts"][0]
    assert impact["confidence_bounds"] == pytest.approx([0.4, 0.6])
    assert impact["exposure_days_range"] == [0, 72]
    assert impact["revenue"][0]["confidence_bounds"] == pytest.approx([0.4, 0.6])

    alternate.update(status="confirmed", confidence=1)
    established = assess(
        frozen.model_copy(update={"data": GraphData.model_validate(values)}),
        "upstream",
        0.9,
        as_of=AS_OF,
    )["impacts"][0]
    assert established["confidence_bounds"] == [1, 1]
    assert established["exposure_days_range"] == [72, 72]
    assert established["revenue"][0]["value_range"] == [3600000, 3600000]


def test_joint_product_and_plant_support_count_shared_upstream_edges_once():
    impact = assess(one_route_snapshot(("dependency-0",)), "upstream", 0.9, as_of=AS_OF)["impacts"][
        0
    ]
    assert impact["confidence_bounds"] == pytest.approx([0.4, 0.4])
    assert impact["revenue"][0]["confidence_bounds"] == pytest.approx([0.4, 0.4])
    assert impact["revenue"][0]["value_range"] == [0, 3600000]


def test_bom_without_product_graph_support_has_explicit_conservative_revenue_range():
    frozen = one_route_snapshot()
    values = frozen.data.model_dump(mode="json")
    values["links"] = [link for link in values["links"] if link["id"] != "used-product"]
    impact = assess(
        frozen.model_copy(update={"data": GraphData.model_validate(values)}),
        "upstream",
        0.9,
        as_of=AS_OF,
    )["impacts"][0]
    assert impact["exposure_days_range"] == [72, 72]
    revenue = impact["revenue"][0]
    assert revenue["value_range"] == [0, 3600000]
    assert revenue["confidence_bounds"] == [0, 1]
    assert revenue["reason"] == "BOM product has no supported where-used graph path."


def test_complete_routes_respect_depth_limit_and_propagate_combination_truncation():
    report = assess(one_route_snapshot(), "upstream", 0.9, as_of=AS_OF, max_depth=2)
    assert report["truncated"]
    assert report["impacts"][0]["truncated"]
    assert report["impacts"][0]["status"] == "incomplete"
    assert report["impacts"][0]["exposure_days_range"] is None

    capped = assess(snapshot(), "upstream", 0.9, as_of=AS_OF, max_paths=1)
    assert capped["truncated"]
    assert capped["impacts"][0]["truncated"]
    assert capped["impacts"][0]["confidence_bounds"][1] == 1
