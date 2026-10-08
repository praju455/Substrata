"""Persistence invariants tested against the migrated SQLite schema."""

from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import delete, func, inspect, select, update
from sqlalchemy.exc import IntegrityError, StatementError

from substrata import models
from substrata.database import Base, build_engine, transaction, upgrade_database
from substrata.models import EdgeEvidence, EvidenceRecord, GraphEdge, GraphNode, SourceSnapshot

AS_OF = datetime(2025, 10, 22, 12, tzinfo=UTC)
PAYLOADS = {
    "Product": {"product_family": "controller", "manufacturer_id": "synthetic_oem"},
    "Component": {"part_number": "CHIP-1", "description": "test chip", "unit": "piece"},
    "SupplierSite": {
        "legal_entity_name": "Synthetic supplier",
        "site_name": "Factory A",
        "country_code": "IN",
    },
    "Plant": {"country_code": "IN", "capacity_unit": "piece/day"},
    "Region": {"region_type": "country"},
    "Event": {
        "event_type": "disruption",
        "observed_at": AS_OF,
        "source_id": "source",
        "severity": 0.5,
    },
    "AlternativeSupplier": {
        "supplier_site_id": "site",
        "component_id": "chip",
        "qualification_status": "pending",
    },
}


def node(node_id, node_type, version=1, **overrides):
    return GraphNode(
        id=node_id,
        graph_version=version,
        node_type=node_type,
        name=node_id,
        normalized_name=node_id.casefold(),
        attributes={"node_type": node_type, **PAYLOADS[node_type], **overrides},
    )


def edge(**overrides):
    values = {
        "id": "supply",
        "graph_version": 1,
        "from_node_id": "site",
        "from_node_type": "SupplierSite",
        "to_node_id": "chip",
        "to_node_type": "Component",
        "edge_type": "SUPPLIES",
        "status": "declared",
        "confidence": 0.72,
        "valid_from": AS_OF,
        "share": 0.5,
        "lead_time_days": 10,
    }
    return GraphEdge(**{**values, **overrides})


@pytest.fixture
def graph_engine(tmp_path: Path):
    engine = build_engine(tmp_path / "graph.sqlite3")
    upgrade_database(engine)
    with transaction(engine) as session:
        session.add_all(
            [
                node("site", "SupplierSite"),
                node("owner", "SupplierSite"),
                node("chip", "Component"),
                node("product", "Product"),
                node("plant", "Plant"),
                node("region", "Region"),
            ]
        )
        session.add(
            SourceSnapshot(
                id="source",
                source_uri="synthetic://test/source",
                source_kind="synthetic",
                observed_at=AS_OF,
                content_sha256="a" * 64,
                permitted_excerpt="Synthetic supplier makes test chips.",
                license_note="Synthetic test fixture, no real supplier claim.",
            )
        )
        session.flush()
        session.add_all(
            [
                EvidenceRecord(id="evidence", source_snapshot_id="source", claim="supports supply"),
                EvidenceRecord(id="other", source_snapshot_id="source", claim="a second claim"),
            ]
        )
    yield engine
    engine.dispose()


@pytest.mark.parametrize("node_type", PAYLOADS)
def test_all_node_types_round_trip_with_validated_attributes(graph_engine, node_type):
    with transaction(graph_engine) as session:
        session.add(node("typed", node_type))
    with transaction(graph_engine) as session:
        loaded = session.get(GraphNode, ("typed", 1))
        assert loaded.synthetic is True
        assert loaded.attributes.node_type == node_type
        assert loaded.attributes.model_dump().keys() >= PAYLOADS[node_type].keys()


@pytest.mark.parametrize(
    "node_type,overrides",
    [
        ("Component", {"unit": " "}),
        ("Component", {"requalification_days": -1}),
        ("Component", {"requalification_days": float("inf")}),
        ("SupplierSite", {"country_code": "India"}),
        ("Product", {"manufacturer_id": ""}),
        ("Region", {"unexpected": True}),
        ("Event", {"observed_at": datetime(2025, 10, 22)}),
        ("Event", {"severity": 1.1}),
        ("AlternativeSupplier", {"qualification_status": "approved_automatically"}),
    ],
)
def test_invalid_entity_attributes_cannot_be_persisted(graph_engine, node_type, overrides):
    with pytest.raises(StatementError), transaction(graph_engine) as session:
        session.add(node("invalid", node_type, **overrides))


def test_node_identity_is_unique_within_version_and_reusable_across_versions(graph_engine):
    with pytest.raises(IntegrityError), transaction(graph_engine) as session:
        session.add(node("chip", "Product"))
    with transaction(graph_engine) as session:
        session.add(node("chip", "Component", version=2, requalification_days=90))
    with transaction(graph_engine) as session:
        assert session.get(GraphNode, ("chip", 1)).attributes.requalification_days is None
        assert session.get(GraphNode, ("chip", 2)).attributes.requalification_days == 90


def test_database_rejects_mismatched_node_kind_and_non_synthetic_entities(graph_engine):
    for values in ({"node_type": "Product"}, {"synthetic": False}, {"graph_version": 0}):
        with pytest.raises(IntegrityError), transaction(graph_engine) as session:
            session.execute(update(GraphNode).where(GraphNode.id == "chip").values(**values))


@pytest.mark.parametrize(
    "values",
    [
        {},
        {
            "edge_type": "USED_IN",
            "from_node_id": "chip",
            "from_node_type": "Component",
            "to_node_id": "product",
            "to_node_type": "Product",
            "share": None,
            "lead_time_days": None,
            "bom_quantity": 2,
            "unit": "piece",
        },
        {
            "edge_type": "USED_IN",
            "from_node_id": "chip",
            "from_node_type": "Component",
            "to_node_id": "plant",
            "to_node_type": "Plant",
            "share": None,
            "lead_time_days": None,
            "bom_quantity": 2,
            "unit": "piece",
        },
        {
            "edge_type": "LOCATED_IN",
            "to_node_id": "region",
            "to_node_type": "Region",
            "share": None,
            "lead_time_days": None,
        },
        {
            "edge_type": "OWNED_BY",
            "to_node_id": "owner",
            "to_node_type": "SupplierSite",
            "share": None,
            "lead_time_days": None,
        },
    ],
)
def test_documented_edge_directions_are_supported(graph_engine, values):
    with transaction(graph_engine) as session:
        session.add(edge(**values))
    with transaction(graph_engine) as session:
        assert session.scalar(select(func.count()).select_from(GraphEdge)) == 1


@pytest.mark.parametrize(
    "values",
    [
        {"confidence": -0.1},
        {"confidence": 1.1},
        {"confidence": float("nan")},
        {"share": None},
        {"share": -0.1},
        {"share": 1.1},
        {"lead_time_days": -1},
        {"status": "approved"},
        {"edge_type": "UNKNOWN"},
        {"valid_to": AS_OF},
        {"valid_to": AS_OF - timedelta(days=1)},
        {"from_node_id": "missing"},
        {"graph_version": 2},
        {"from_node_id": "product"},
        {"from_node_id": "product", "from_node_type": "Product"},
        {"bom_quantity": 2, "unit": "piece"},
        {"status": "inferred"},
        {"status": "inferred", "primary_evidence_id": "missing"},
        {"status": "confirmed"},
    ],
)
def test_invalid_edges_are_rejected_by_database(graph_engine, values):
    with pytest.raises(IntegrityError), transaction(graph_engine) as session:
        session.add(edge(**values))


def test_infinite_lead_time_is_rejected(graph_engine):
    with pytest.raises(IntegrityError), transaction(graph_engine) as session:
        session.add(edge(lead_time_days=float("inf")))


def test_duplicate_relationship_at_same_version_and_start_is_rejected(graph_engine):
    with transaction(graph_engine) as session:
        session.add(edge())
    with pytest.raises(IntegrityError), transaction(graph_engine) as session:
        session.add(edge(id="same_relationship_different_id"))


def test_orphan_evidence_and_cross_version_links_are_rejected(graph_engine):
    with pytest.raises(IntegrityError), transaction(graph_engine) as session:
        session.add(EvidenceRecord(id="orphan", source_snapshot_id="missing", claim="unsupported"))
    with transaction(graph_engine) as session:
        session.add(edge())
    with pytest.raises(IntegrityError), transaction(graph_engine) as session:
        session.add(EdgeEvidence(edge_id="supply", graph_version=2, evidence_id="evidence"))


@pytest.mark.parametrize("values", [{"bom_quantity": None}, {"bom_quantity": 0}, {"unit": " "}])
def test_bom_requires_positive_quantity_and_unit(graph_engine, values):
    with pytest.raises(IntegrityError), transaction(graph_engine) as session:
        session.add(
            edge(
                **{
                    "edge_type": "USED_IN",
                    "from_node_id": "chip",
                    "from_node_type": "Component",
                    "to_node_id": "plant",
                    "to_node_type": "Plant",
                    "share": None,
                    "lead_time_days": None,
                    "bom_quantity": 2,
                    "unit": "piece",
                    **values,
                }
            )
        )


def test_inferred_edge_has_traceable_primary_and_conflicting_evidence(graph_engine):
    with transaction(graph_engine) as session:
        session.add(edge(status="inferred", primary_evidence_id="evidence"))
        session.flush()
        session.add(
            EdgeEvidence(
                edge_id="supply", graph_version=1, evidence_id="other", stance="contradicts"
            )
        )
    with transaction(graph_engine) as session:
        source = session.scalar(
            select(SourceSnapshot)
            .join(EvidenceRecord)
            .join(EdgeEvidence)
            .where(EdgeEvidence.edge_id == "supply", EdgeEvidence.stance == "supports")
        )
        assert source.source_uri == "synthetic://test/source"
        assert source.content_sha256 == "a" * 64
        assert session.get(GraphEdge, ("supply", 1)).status == "inferred"
        assert session.scalar(select(func.count()).select_from(EdgeEvidence)) == 2


def test_primary_evidence_cannot_be_removed_or_changed(graph_engine):
    with transaction(graph_engine) as session:
        session.add(edge(status="inferred", primary_evidence_id="evidence"))
    for statement in (
        delete(EdgeEvidence),
        update(EdgeEvidence).values(stance="contradicts"),
        delete(EvidenceRecord).where(EvidenceRecord.id == "evidence"),
    ):
        with pytest.raises(IntegrityError), transaction(graph_engine) as session:
            session.execute(statement)
    with transaction(graph_engine) as session:
        assert session.get(EdgeEvidence, ("supply", 1, "evidence")).stance == "supports"


def test_changing_primary_citation_preserves_prior_evidence(graph_engine):
    with transaction(graph_engine) as session:
        session.add(edge(status="inferred", primary_evidence_id="evidence"))
    with transaction(graph_engine) as session:
        session.get(GraphEdge, ("supply", 1)).primary_evidence_id = "other"
    with transaction(graph_engine) as session:
        assert session.get(EdgeEvidence, ("supply", 1, "other")).stance == "supports"
        assert session.get(EdgeEvidence, ("supply", 1, "evidence")) is not None


def test_conflicting_evidence_cannot_be_promoted_to_primary(graph_engine):
    with transaction(graph_engine) as session:
        session.add(edge(status="inferred", primary_evidence_id="evidence"))
        session.flush()
        session.add(
            EdgeEvidence(
                edge_id="supply", graph_version=1, evidence_id="other", stance="contradicts"
            )
        )
    with pytest.raises(IntegrityError, match="must support"), transaction(graph_engine) as session:
        session.get(GraphEdge, ("supply", 1)).primary_evidence_id = "other"
    with transaction(graph_engine) as session:
        assert session.get(GraphEdge, ("supply", 1)).primary_evidence_id == "evidence"


@pytest.mark.parametrize("status", ["declared", "inferred"])
def test_confirmation_is_blocked_until_human_workflow_exists(graph_engine, status):
    with transaction(graph_engine) as session:
        session.add(edge(status=status, primary_evidence_id="evidence"))
    with pytest.raises(IntegrityError, match="workflow"), transaction(graph_engine) as session:
        session.execute(update(GraphEdge).values(status="confirmed", last_verified=AS_OF))
    with transaction(graph_engine) as session:
        assert session.get(GraphEdge, ("supply", 1)).status == status


@pytest.mark.parametrize("status", ["rejected", "expired"])
def test_rejection_and_expiry_retain_the_edge_and_evidence(graph_engine, status):
    with transaction(graph_engine) as session:
        session.add(edge(status="inferred", primary_evidence_id="evidence"))
    with transaction(graph_engine) as session:
        session.get(GraphEdge, ("supply", 1)).status = status
    with transaction(graph_engine) as session:
        assert session.get(GraphEdge, ("supply", 1)).status == status
        assert session.get(EdgeEvidence, ("supply", 1, "evidence")) is not None


@pytest.mark.parametrize(
    "values",
    [
        {"content_sha256": "not-a-hash"},
        {"content_sha256": "z" * 64},
        {"license_note": " "},
        {"permitted_excerpt": ""},
        {"source_kind": "live_verified"},
    ],
)
def test_source_provenance_constraints(graph_engine, values):
    with pytest.raises(IntegrityError), transaction(graph_engine) as session:
        session.execute(update(SourceSnapshot).values(**values))


def test_timestamps_round_trip_as_utc_and_naive_dates_are_rejected(graph_engine):
    offset = AS_OF.astimezone(timezone(timedelta(hours=5, minutes=30)))
    with transaction(graph_engine) as session:
        session.execute(update(SourceSnapshot).values(observed_at=offset))
    with transaction(graph_engine) as session:
        assert session.get(SourceSnapshot, "source").observed_at == AS_OF
        assert session.get(SourceSnapshot, "source").observed_at.tzinfo is UTC
    with (
        pytest.raises(StatementError, match="timezone-aware"),
        transaction(graph_engine) as session,
    ):
        session.execute(update(SourceSnapshot).values(observed_at=datetime(2025, 10, 22)))


def test_migration_matches_orm_and_can_rebuild_from_baseline(tmp_path):
    engine = build_engine(tmp_path / "migration.sqlite3")
    config = Config()
    config.set_main_option("script_location", str(Path(models.__file__).parent / "migrations"))
    try:
        upgrade_database(engine)
        with engine.begin() as connection:
            assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
            config.attributes["connection"] = connection
            command.downgrade(config, "0001_database_baseline")
            assert inspect(connection).get_table_names() == ["alembic_version"]
        upgrade_database(engine)
        with engine.connect() as connection:
            assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
    finally:
        engine.dispose()
