"""Tenant collisions, historical reads, atomic changes and passage integrity."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from substrata.platform.database import build_engine, migrate
from substrata.platform.domain import Citation, Entity, GraphData, Link, Measure, Provenance
from substrata.platform.store import Conflict, PlatformStore


@pytest.fixture
def platform(tmp_path):
    engine = build_engine(f"sqlite:///{(tmp_path / 'platform.sqlite3').as_posix()}")
    migrate(engine)
    migrate(engine)
    store = PlatformStore(engine)
    for tenant in ("alpha", "beta"):
        store.provision(tenant, tenant.title(), "test-admin")
    yield store
    engine.dispose()


def source():
    return Provenance(
        uri="synthetic://test",
        observed_at=datetime.now(UTC),
        kind="synthetic",
        note="Invented test data",
    )


def graph(name="Example"):
    return GraphData(
        entities=[Entity(id="supplier", kind="Supplier", name=name, provenance=source())]
    )


def test_same_ids_are_isolated_and_unknown_tenant_cannot_read(platform):
    platform.save("alpha", graph("First"), "analyst", expected_version=0)
    platform.save("beta", graph("Second"), "analyst", expected_version=0)
    assert platform.snapshot("alpha").data.entities[0].name == "First"
    assert platform.snapshot("beta").data.entities[0].name == "Second"
    with pytest.raises(ValueError, match="No graph"):
        platform.snapshot("unknown")
    assert all(r["payload"]["tenant_id"] == "alpha" for r in platform.audit("alpha")["records"])


def test_immutable_history_and_as_of(platform):
    before = datetime.now(UTC) - timedelta(seconds=1)
    first = platform.save("alpha", graph("Before"), "analyst", expected_version=0)
    platform.save("alpha", graph("After"), "analyst", expected_version=1)
    assert platform.snapshot("alpha", as_of=first.recorded_at).data.entities[0].name == "Before"
    assert platform.snapshot("alpha", version=1).sha256 == first.sha256
    with pytest.raises(ValueError, match="No graph"):
        platform.snapshot("alpha", as_of=before)
    with pytest.raises(ValueError, match="timezone"):
        platform.snapshot("alpha", as_of=datetime.now())
    with pytest.raises(DBAPIError), platform.engine.begin() as connection:
        connection.execute(text("UPDATE graph_revisions SET sha256 = 'tampered'"))


def test_stale_write_has_no_graph_or_audit_effect(platform):
    platform.save("alpha", graph(), "analyst", expected_version=0)
    head = platform.audit("alpha")["verification"]["head"]
    with pytest.raises(Conflict):
        platform.save("alpha", graph("Stale"), "analyst", expected_version=0)
    assert platform.snapshot("alpha").version == 1
    assert platform.audit("alpha", head)["verification"]["valid"]
    assert not platform.audit("alpha", "0" * 64)["verification"]["valid"]


def test_passages_cannot_reference_other_tenant_documents(platform):
    passage = "Supplier depends on a shared site."
    platform.add_document("beta", "filing", passage, source(), "analyst")
    entities = [Entity(id=id, kind="Supplier", name=id, provenance=source()) for id in ("s", "t")]
    link = Link(
        id="dependency",
        source="s",
        target="t",
        type="DEPENDS_ON",
        confidence=0.7,
        status="inferred",
        provenance=source(),
        valid_from=datetime.now(UTC),
        evidence=[Citation(document_id="filing", passage=passage, start=0, end=len(passage))],
    )
    data = GraphData(entities=entities, links=[link])
    with pytest.raises(ValueError, match="citation"):
        platform.save("alpha", data, "analyst", expected_version=0)
    assert platform.audit("alpha")["verification"]["count"] == 1
    platform.add_document("alpha", "filing", passage, source(), "analyst")
    platform.save("alpha", data, "analyst", expected_version=0)
    with pytest.raises(Conflict):
        platform.add_document("alpha", "filing", "Changed", source(), "analyst")


def test_invalid_numbers_and_missing_provenance_are_rejected():
    for value in (float("inf"), float("nan"), -1):
        with pytest.raises(ValueError):
            Measure(value=value, unit="kg", provenance=source())
    with pytest.raises(ValueError):
        Measure(value=4, unit="kg")
    with pytest.raises(ValueError, match="endpoint"):
        GraphData(
            links=[
                Link(
                    id="link",
                    source="absent",
                    target="other",
                    type="SUPPLIES",
                    confidence=1,
                    status="declared",
                    provenance=source(),
                    valid_from=datetime.now(UTC),
                )
            ]
        )


def test_database_enforces_append_only_audit(platform):
    with pytest.raises(DBAPIError), platform.engine.begin() as connection:
        connection.execute(text("DELETE FROM platform_audit WHERE tenant_id='alpha'"))
    assert platform.audit("alpha")["verification"]["valid"]
