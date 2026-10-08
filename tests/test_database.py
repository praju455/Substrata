"""Exercise real file-backed SQLite behavior without creating demo records."""

from pathlib import Path

import pytest
from sqlalchemy import Column, ForeignKey, Integer, MetaData, Table, inspect, select, text
from sqlalchemy.exc import IntegrityError

from substrata.database import build_engine, transaction, upgrade_database


@pytest.fixture
def engine(tmp_path: Path):
    database = build_engine(tmp_path / "nested" / "test.sqlite3")
    yield database
    database.dispose()


@pytest.fixture
def probe_table(engine):
    # Test-only schema: application domain tables arrive in the next checkpoint.
    table = Table("probe", MetaData(), Column("id", Integer, primary_key=True))
    table.metadata.create_all(engine)
    return table


def test_connection_settings_apply_to_every_connection(engine):
    with engine.connect() as first, engine.connect() as second:
        for connection in (first, second):
            assert connection.exec_driver_sql("PRAGMA journal_mode").scalar_one() == "wal"
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
            assert connection.exec_driver_sql("PRAGMA busy_timeout").scalar_one() == 5000


def test_foreign_keys_reject_orphan_rows(engine):
    metadata = MetaData()
    Table("parent", metadata, Column("id", Integer, primary_key=True))
    child = Table("child", metadata, Column("parent_id", ForeignKey("parent.id")))
    metadata.create_all(engine)
    with pytest.raises(IntegrityError), transaction(engine) as session:
        session.execute(child.insert().values(parent_id=999))


def test_transaction_commits_and_rolls_back_failed_work(engine, probe_table):
    with transaction(engine) as session:
        session.execute(probe_table.insert().values(id=1))
    with pytest.raises(ValueError, match="abandon"), transaction(engine) as session:
        session.execute(probe_table.insert().values(id=2))
        raise ValueError("abandon this unit of work")
    with transaction(engine) as session:
        assert session.scalars(select(probe_table.c.id)).all() == [1]


def test_wal_reader_can_read_during_an_uncommitted_write(engine, probe_table):
    with transaction(engine) as session:
        session.execute(probe_table.insert().values(id=1))
    with transaction(engine) as writer:
        writer.execute(probe_table.insert().values(id=2))
        with transaction(engine) as reader:
            assert reader.scalars(select(probe_table.c.id)).all() == [1]
    with transaction(engine) as reader:
        assert reader.scalars(select(probe_table.c.id).order_by(probe_table.c.id)).all() == [1, 2]


def test_migration_is_repeatable_and_preserves_records(engine, probe_table):
    with transaction(engine) as session:
        session.execute(probe_table.insert().values(id=7))
    upgrade_database(engine)
    upgrade_database(engine)
    engine.dispose()
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0005_governed_replay"
        )
        assert connection.execute(select(probe_table.c.id)).scalar_one() == 7


def test_fresh_database_has_current_graph_schema(engine):
    upgrade_database(engine)
    assert set(inspect(engine).get_table_names()) >= {
        "alembic_version",
        "bom_items",
        "edge_evidence",
        "erp_datasets",
        "evidence_records",
        "graph_edges",
        "graph_nodes",
        "lead_times",
        "plant_stock",
        "purchasing_documents",
        "source_snapshots",
        "vendor_master",
        "agent_runs",
        "confirmation_requests",
        "confirmation_responses",
        "evaluation_runs",
        "evaluation_examples",
        "evaluation_metrics",
        "tool_calls",
    }
