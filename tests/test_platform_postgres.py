"""Run tenant row-level security checks against real PostgreSQL in CI."""

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError

from substrata.platform.database import build_engine, migrate, tenant_transaction
from substrata.platform.models import WorkRecord
from substrata.platform.store import PlatformStore

ADMIN_URL = os.environ.get("SUBSTRATA_TEST_POSTGRES_ADMIN_URL")
RUNTIME_ROLE = "substrata_test_runtime"
RUNTIME_PASSWORD = "test-only-substrata-runtime-password"


@pytest.fixture(scope="module")
def postgres_store():
    if not ADMIN_URL:
        pytest.skip("Set SUBSTRATA_TEST_POSTGRES_ADMIN_URL to run PostgreSQL RLS checks.")
    admin_engine = build_engine(ADMIN_URL)
    migrate(admin_engine)
    database = make_url(ADMIN_URL).database
    quoted_database = admin_engine.dialect.identifier_preparer.quote(database)
    with admin_engine.begin() as connection:
        exists = connection.scalar(
            text("SELECT 1 FROM pg_roles WHERE rolname = :name"), {"name": RUNTIME_ROLE}
        )
        if exists:
            connection.exec_driver_sql(
                f"ALTER ROLE {RUNTIME_ROLE} LOGIN NOSUPERUSER NOBYPASSRLS "
                f"PASSWORD '{RUNTIME_PASSWORD}'"
            )
        else:
            connection.exec_driver_sql(
                f"CREATE ROLE {RUNTIME_ROLE} LOGIN NOSUPERUSER NOBYPASSRLS "
                f"PASSWORD '{RUNTIME_PASSWORD}'"
            )
        connection.exec_driver_sql(f"GRANT CONNECT ON DATABASE {quoted_database} TO {RUNTIME_ROLE}")
        connection.exec_driver_sql(f"GRANT USAGE ON SCHEMA public TO {RUNTIME_ROLE}")
        connection.exec_driver_sql(
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {RUNTIME_ROLE}"
        )
        connection.exec_driver_sql(
            f"GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO {RUNTIME_ROLE}"
        )
    runtime_url = (
        make_url(ADMIN_URL)
        .set(username=RUNTIME_ROLE, password=RUNTIME_PASSWORD)
        .render_as_string(hide_password=False)
    )
    runtime_engine = build_engine(runtime_url)
    try:
        yield PlatformStore(runtime_engine), admin_engine
    finally:
        runtime_engine.dispose()
        admin_engine.dispose()


def test_postgres_forces_tenant_isolation_for_runtime_role(postgres_store):
    store, admin_engine = postgres_store
    with pytest.raises(ValueError, match="must not be superuser or BYPASSRLS"):
        PlatformStore(admin_engine)

    alpha = f"rls-alpha-{uuid4().hex}"
    beta = f"rls-beta-{uuid4().hex}"
    store.provision(alpha, "Alpha", "test-admin")
    store.provision(beta, "Beta", "test-admin")
    with tenant_transaction(store.engine, alpha) as session:
        session.add(
            WorkRecord(
                tenant_id=alpha,
                id="visible-alpha",
                kind="test",
                status="ready",
                created_at=datetime.now(UTC),
                payload={},
            )
        )
    with tenant_transaction(store.engine, beta) as session:
        session.add(
            WorkRecord(
                tenant_id=beta,
                id="visible-beta",
                kind="test",
                status="ready",
                created_at=datetime.now(UTC),
                payload={},
            )
        )

    with tenant_transaction(store.engine, alpha) as session:
        visible = {row.id for row in session.scalars(select(WorkRecord))}
        assert visible == {"visible-alpha"}
    with pytest.raises(DBAPIError):
        with tenant_transaction(store.engine, alpha) as session:
            session.add(
                WorkRecord(
                    tenant_id=beta,
                    id="cross-tenant-write",
                    kind="test",
                    status="ready",
                    created_at=datetime.now(UTC),
                    payload={},
                )
            )
            session.flush()
    assert store.audit(alpha)["verification"]["valid"]
