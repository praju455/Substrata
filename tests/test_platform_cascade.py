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
