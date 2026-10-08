"""ERP quantities retain missing values and reject impossible inputs."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from substrata.database import build_engine, transaction, upgrade_database
from substrata.erp_models import Dataset, LeadTime, PlantStock
from substrata.models import GraphNode

AS_OF = datetime(2025, 10, 22, tzinfo=UTC)


@pytest.fixture
def erp_engine(tmp_path):
    engine = build_engine(tmp_path / "erp.sqlite3")
    upgrade_database(engine)
    with transaction(engine) as session:
        session.add_all(
            [
                GraphNode(
                    id="chip",
                    graph_version=1,
                    node_type="Component",
                    name="Chip",
                    normalized_name="chip",
                    attributes={
                        "node_type": "Component",
                        "part_number": "CHIP",
                        "description": "Synthetic chip",
                        "unit": "piece",
                    },
                ),
                GraphNode(
                    id="plant",
                    graph_version=1,
                    node_type="Plant",
                    name="Plant",
                    normalized_name="plant",
                    attributes={
                        "node_type": "Plant",
                        "country_code": "IN",
                        "capacity_unit": "piece/day",
                    },
                ),
                Dataset(
                    id="demo-v1", graph_version=1, inventory_snapshot_id="stock-v1", as_of=AS_OF
                ),
            ]
        )
    yield engine
    engine.dispose()


def stock(**changes):
    return PlantStock(
        **{
            "dataset_version": "demo-v1",
            "component_id": "chip",
            "plant_id": "plant",
            "graph_version": 1,
            "inventory_snapshot_id": "stock-v1",
            "as_of": AS_OF,
            "on_hand": None,
            "daily_consumption": 0,
            "unit": "piece",
            **changes,
        }
    )


def test_missing_inventory_and_zero_consumption_remain_distinct(erp_engine):
    with transaction(erp_engine) as session:
        session.add(stock())
    with transaction(erp_engine) as session:
        row = session.get(PlantStock, ("demo-v1", "chip", "plant"))
        assert row.on_hand is None
        assert row.daily_consumption == 0
        assert row.as_of == AS_OF


@pytest.mark.parametrize(
    "changes",
    [
        {"on_hand": -1},
        {"daily_consumption": -1},
        {"on_hand": float("inf")},
        {"unit": " "},
        {"component_id": "absent"},
        {"dataset_version": "absent"},
    ],
)
def test_invalid_stock_is_rejected(erp_engine, changes):
    with pytest.raises(IntegrityError), transaction(erp_engine) as session:
        session.add(stock(**changes))


def test_lead_time_requires_provenance_and_nonnegative_time(erp_engine):
    for days, provenance in [(-1, "synthetic assumption"), (90, " ")]:
        with pytest.raises(IntegrityError), transaction(erp_engine) as session:
            session.add(
                LeadTime(
                    dataset_version="demo-v1",
                    component_id="chip",
                    graph_version=1,
                    requalification_days=days,
                    provenance=provenance,
                )
            )
