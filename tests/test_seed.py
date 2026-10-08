"""Seed reproducibility, truth isolation and transactional reset recovery."""

import json

import pytest
from sqlalchemy import func, select

from substrata.database import build_engine, transaction, upgrade_database
from substrata.erp_models import PlantStock
from substrata.models import GraphEdge, GraphNode
from substrata.seed import generate_fixture, seed_database, write_fixtures


def test_generator_is_fixed_and_masks_only_hidden_edges():
    first = generate_fixture()
    assert first == generate_fixture()
    declared, truth, corpus, events = first
    assert len([n for n in declared["nodes"] if n["node_type"] == "SupplierSite"]) == 12
    assert len([n for n in declared["nodes"] if n["node_type"] == "Component"]) == 8
    hidden_ids = {e["id"] for e in truth["edges"] if e["hidden"]}
    assert len(hidden_ids) == 4
    assert not hidden_ids & {e["id"] for e in declared["edges"]}
    assert all("hidden" not in e for e in declared["edges"])
    assert len(corpus) == 7
    assert len(events) == 6
    assert all("SYNTHETIC" in item["text"] for item in corpus)


def test_reset_is_repeatable_and_truth_is_not_loaded(tmp_path):
    fingerprint = write_fixtures(tmp_path)
    engine = build_engine(tmp_path / "seed.sqlite3")
    try:
        upgrade_database(engine)
        assert seed_database(engine, tmp_path) == fingerprint
        assert seed_database(engine, tmp_path) == fingerprint
        with transaction(engine) as session:
            assert session.scalar(select(func.count()).select_from(GraphNode)) == 32
            assert session.scalar(select(func.count()).select_from(PlantStock)) == 16
            assert session.get(GraphEdge, ("owned_by_site_t2_0_site_shared_source", 1)) is None
            stock = session.get(PlantStock, ("synthetic-v1", "component_0", "plant_0"))
            assert stock.on_hand == 1200
    finally:
        engine.dispose()


def test_failed_reset_rolls_back_schema_and_existing_data(tmp_path):
    write_fixtures(tmp_path)
    engine = build_engine(tmp_path / "seed.sqlite3")
    try:
        upgrade_database(engine)
        seed_database(engine, tmp_path)
        corpus_path = tmp_path / "corpus.json"
        corpus = json.loads(corpus_path.read_text())
        del corpus[0]["reliability"]
        corpus_path.write_text(json.dumps(corpus))
        with pytest.raises(KeyError):
            seed_database(engine, tmp_path)
        with transaction(engine) as session:
            assert session.scalar(select(func.count()).select_from(PlantStock)) == 16
            assert (
                session.get(GraphNode, ("site_shared_source", 1)).name == "Meridian Semiconductors"
            )
    finally:
        engine.dispose()
