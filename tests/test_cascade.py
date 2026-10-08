"""Curated graph math, runway and snapshot/unit edge cases."""

import networkx as nx
import pytest
from sqlalchemy import delete, update

from substrata.cascade import cascade, runway
from substrata.database import build_engine, transaction, upgrade_database
from substrata.erp_models import PlantStock
from substrata.graph import NetworkXGraphStore, dependency_paths
from substrata.seed import AS_OF, seed_database, write_fixtures


@pytest.fixture
def seeded_engine(tmp_path):
    write_fixtures(tmp_path)
    engine = build_engine(tmp_path / "cascade.sqlite3")
    upgrade_database(engine)
    seed_database(engine, tmp_path)
    yield engine
    engine.dispose()


def test_worked_example_and_missing_or_zero_demand():
    assert runway(1200, 600, 100, 90) == ("complete", 18, 72)
    assert runway(None, 600, 100, 90) == ("incomplete", None, None)
    assert runway(1200, 600, 0, 90) == ("no_demand", None, 0)
    assert runway(1200, 600, 100, 10) == ("complete", 18, 0)
    with pytest.raises(ValueError):
        runway(-1, 0, 1, 90)
    with pytest.raises(ValueError):
        runway(float("inf"), 0, 1, 90)


def test_multiple_paths_product_noisy_or_and_cycles():
    graph = nx.MultiDiGraph()
    graph.add_edge("a", "b", key="ab", confidence=0.8)
    graph.add_edge("b", "d", key="bd", confidence=0.5)
    graph.add_edge("a", "c", key="ac", confidence=0.6)
    graph.add_edge("c", "d", key="cd", confidence=0.5)
    graph.add_edge("b", "a", key="cycle", confidence=1)
    result = dependency_paths(graph, "a", "d")
    assert [p.confidence for p in result.paths] == [0.4, 0.3]
    assert result.confidence == pytest.approx(0.58)
    assert result.truncated is False
    assert dependency_paths(graph, "a", "d", max_depth=1).truncated
    assert dependency_paths(graph, "a", "d", max_paths=1).truncated
    assert dependency_paths(graph, "a", "absent").paths == []


def test_real_snapshot_runway_and_unit_mismatch(seeded_engine):
    store = NetworkXGraphStore(seeded_engine)
    # Direct site event reaches the part without requiring hidden truth.
    result = cascade(seeded_engine, store.snapshot(), "site_t1_0", 0.9)
    first = result.impacts[0]
    assert first.cover_days == 18
    assert first.exposure_window == 72
    assert first.priority == 72
    with transaction(seeded_engine) as session:
        session.execute(
            update(PlantStock).where(PlantStock.component_id == "component_0").values(unit="kg")
        )
    result = cascade(seeded_engine, store.snapshot(), "site_t1_0", 0.9)
    assert result.impacts[0].status == "incomplete"
    assert result.impacts[0].cover_days is None


def test_hidden_parent_is_not_visible_before_mapping(seeded_engine):
    store = NetworkXGraphStore(seeded_engine)
    assert cascade(seeded_engine, store.snapshot(), "site_shared_source", 0.9).impacts == []
    store.propose_edge(
        {
            "id": "inferred_parent",
            "graph_version": 1,
            "from_node_id": "site_t2_0",
            "from_node_type": "SupplierSite",
            "to_node_id": "site_shared_source",
            "to_node_type": "SupplierSite",
            "edge_type": "OWNED_BY",
            "status": "inferred",
            "confidence": 0.8,
            "valid_from": AS_OF,
            "primary_evidence_id": "evidence_0",
        }
    )
    result = cascade(seeded_engine, store.snapshot(), "site_shared_source", 0.9)
    assert len(result.impacts) == 4  # Site 0 supplies components 0 and 6 to two plants.
    assert result.impacts[0].path_confidence == pytest.approx(0.8)
    assert result.impacts[0].evidence_ids == ["evidence_0"]


def test_missing_inventory_row_is_incomplete_not_unaffected(seeded_engine):
    with transaction(seeded_engine) as session:
        session.execute(delete(PlantStock).where(PlantStock.component_id == "component_0"))
    result = cascade(seeded_engine, NetworkXGraphStore(seeded_engine).snapshot(), "site_t1_0", 0.9)
    assert result.impacts[0].status == "incomplete"
    assert result.impacts[0].reason == "Inventory row is missing."
