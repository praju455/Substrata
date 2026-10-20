"""Production-dialect workflow and isolation checks against PostgreSQL/pgvector."""

import base64
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from test_platform_store import graph, source

from substrata.platform.auth import Principal
from substrata.platform.database import build_engine, migrate, tenant_transaction
from substrata.platform.domain import Measure
from substrata.platform.evidence import index_documents, retrieve
from substrata.platform.governance import (
    Policy,
    ProposalInput,
    configure_policy,
    decide,
    execute,
    propose,
    save_assessment,
)
from substrata.platform.ingestion import TabularImport, apply_import, rollback, stage
from substrata.platform.jobs import JobInput, enqueue, jobs, run_next
from substrata.platform.models import (
    AuditRecord,
    Base,
    Document,
    DocumentChunk,
    GraphRevision,
    Organisation,
    WorkRecord,
)
from substrata.platform.records import list_records
from substrata.platform.seeds import generate
from substrata.platform.store import Conflict, PlatformStore

ADMIN_URL = os.environ.get("SUBSTRATA_TEST_POSTGRES_ADMIN_URL")
RUNTIME_ROLE = "substrata_test_runtime"
RUNTIME_PASSWORD = "test-only-substrata-runtime-password"


@pytest.mark.parametrize("late_failure", [False, True])
def test_postgres_reclaimed_job_preserves_new_attempt(postgres_tenants, monkeypatch, late_failure):
    from test_platform_job_leases import exercise_reclaimed_job

    store, tenant, _ = postgres_tenants
    exercise_reclaimed_job(store, tenant, monkeypatch, late_failure)


@pytest.fixture(scope="module")
def postgres_store():
    if not ADMIN_URL:
        pytest.skip("Set SUBSTRATA_TEST_POSTGRES_ADMIN_URL to run PostgreSQL RLS checks.")
    admin_engine = build_engine(ADMIN_URL)
    migrate(admin_engine)
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


@pytest.fixture
def postgres_tenants(postgres_store):
    store, _ = postgres_store
    suffix = uuid4().hex
    alpha, beta = f"pg-alpha-{suffix}", f"pg-beta-{suffix}"
    store.provision(alpha, "Synthetic Alpha", "test-admin")
    store.provision(beta, "Synthetic Beta", "test-admin")
    return store, alpha, beta


class FixtureEmbeddings:
    """Constant synthetic vectors exercise SQL cosine retrieval without a provider."""

    def __init__(self, model="synthetic-fixture-v1"):
        self.model = model

    def embed(self, texts):
        return [[1.0] + [0.0] * 383 for _ in texts]


def principal(tenant, subject="analyst", role="analyst"):
    return Principal(subject=subject, tenant_id=tenant, roles={role})


def test_postgres_rls_is_forced_on_every_tenant_table_and_unset_context_denies_reads(
    postgres_store, postgres_tenants
):
    store, alpha, beta = postgres_tenants
    _, admin_engine = postgres_store
    for tenant in (alpha, beta):
        store.save(tenant, graph(tenant), "analyst", expected_version=0)
        store.add_document(tenant, "same-document-id", tenant, source(), "analyst")
        index_documents(store, principal(tenant), embedder=FixtureEmbeddings())
        with tenant_transaction(store.engine, tenant) as session:
            session.add(
                WorkRecord(
                    tenant_id=tenant,
                    id="same-work-id",
                    kind="test",
                    status="ready",
                    created_at=datetime.now(UTC),
                    payload={},
                )
            )

    with admin_engine.connect() as connection:
        for table in Base.metadata.tables:
            flags = connection.execute(
                text(
                    "SELECT relrowsecurity, relforcerowsecurity FROM pg_class "
                    "WHERE oid = to_regclass(:table)"
                ),
                {"table": f"public.{table}"},
            ).one()
            assert flags == (True, True), table

    models = (Organisation, GraphRevision, AuditRecord, Document, DocumentChunk, WorkRecord)
    assert {model.__tablename__ for model in models} == set(Base.metadata.tables)
    for tenant, other in ((alpha, beta), (beta, alpha)):
        with tenant_transaction(store.engine, tenant) as session:
            for model in models:
                rows = list(session.scalars(select(model)))  # Deliberately omit a tenant WHERE.
                assert rows and {row.tenant_id for row in rows} == {tenant}, model.__name__
                assert not list(session.scalars(select(model).where(model.tenant_id == other)))

    # Borrow from the same pool after both tenant transactions committed. SET LOCAL
    # must not leak a tenant into a later operation with no authenticated context.
    with store.engine.connect() as connection:
        for table in Base.metadata.tables:
            assert connection.scalar(text(f"SELECT count(*) FROM {table}")) == 0, table


def test_postgres_recursive_paths_match_offline_traversal(postgres_tenants):
    store, alpha, beta = postgres_tenants
    as_of = datetime.now(UTC)
    store.save(alpha, generate("automotive", as_of=as_of), "analyst", expected_version=0)
    store.save(beta, generate("food", as_of=as_of), "analyst", expected_version=0)
    result = store.paths(
        alpha,
        "upstream",
        "plant",
        version=1,
        traversal_as_of=as_of,
        max_depth=8,
        max_paths=128,
        budget=10000,
    )
    assert sorted(path.nodes for path in result.paths) == [
        ["upstream", "supplier-0", "material", "plant"],
        ["upstream", "supplier-1", "material", "plant"],
        ["upstream", "supplier-2", "material", "plant"],
    ]
    assert not result.truncated
    assert store.paths(
        beta,
        "upstream",
        "plant",
        version=1,
        traversal_as_of=as_of,
    ).paths


def test_postgres_assessment_matches_offline_cascade(postgres_tenants):
    from substrata.platform.cascade import assess

    store, alpha, _ = postgres_tenants
    as_of = datetime.now(UTC)
    snapshot = store.save(alpha, generate("automotive", as_of=as_of), "analyst", expected_version=0)
    expected = assess(snapshot, "upstream", 0.8, as_of=as_of)
    saved = save_assessment(
        store,
        principal(alpha),
        "upstream",
        0.8,
        as_of=as_of,
        version=snapshot.version,
    )
    assert saved["payload"]["report"] == expected


def test_postgres_execution_budget_is_serialized_across_workers(postgres_tenants, monkeypatch):
    store, alpha, _ = postgres_tenants
    provenance = source()

    def measure(value, unit):
        return Measure(value=value, unit=unit, provenance=provenance)

    admin = principal(alpha, subject="admin", role="admin")
    configure_policy(
        store,
        admin,
        Policy(
            currency="USD",
            spend_limit=measure(1000, "USD"),
            auto_approve_limit=measure(100, "USD"),
            approval_sla=measure(24, "hour"),
            job_hourly_limit=1,
            job_timeout_seconds=30,
        ),
    )
    for key in ("postgres-budget-1", "postgres-budget-2"):
        enqueue(store, admin, JobInput(kind="event_poll", idempotency_key=key))
    monkeypatch.setattr("substrata.platform.events.poll", lambda platform, tenant: [])

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: run_next(store, admin), range(2)))

    assert sum(result is not None for result in results) == 1
    assert [row["status"] for row in jobs(store, alpha)].count("pending") == 1
    budget = list_records(store, alpha, kind="execution_budget")
    assert len(budget) == 1
    assert budget[0]["payload"]["used"] == 1


def test_postgres_pgvector_roundtrip_search_and_embedding_versions_are_tenant_scoped(
    postgres_tenants,
):
    store, alpha, beta = postgres_tenants
    embedder = FixtureEmbeddings()
    for tenant in (alpha, beta):
        content = f"Synthetic evidence belonging only to {tenant}."
        store.add_document(tenant, "filing", content, source(), "analyst")
        assert index_documents(store, principal(tenant), embedder)["indexed_chunks"] == 1
        assert index_documents(store, principal(tenant), embedder)["indexed_chunks"] == 0
        hits = retrieve(store, tenant, "Synthetic evidence", embedder=embedder)
        assert len(hits) == 1
        assert hits[0]["text"] == content
        assert hits[0]["score"] == pytest.approx(1.0)
        assert content[hits[0]["start"] : hits[0]["end"]] == hits[0]["text"]

    updated = FixtureEmbeddings(model="synthetic-fixture-v2")
    assert index_documents(store, principal(alpha), updated)["indexed_chunks"] == 1
    with tenant_transaction(store.engine, alpha) as session:
        chunks = list(session.scalars(select(DocumentChunk)))
        assert {chunk.embedding_model for chunk in chunks} == {embedder.model, updated.model}
        assert all(chunk.embedding == [1.0] + [0.0] * 383 for chunk in chunks)
        assert (
            session.scalar(text("SELECT pg_typeof(embedding)::text FROM document_chunks LIMIT 1"))
            == "vector"
        )
    # A new embedding version for Alpha must not index Beta's documents.
    assert retrieve(store, beta, "Synthetic evidence", embedder=updated) == []
    assert retrieve(store, alpha, "Synthetic evidence", embedder=embedder)[0]["text"].endswith(
        f"{alpha}."
    )


def test_postgres_import_history_idempotency_and_rollback_preserve_graph_and_audit(
    postgres_tenants,
):
    store, alpha, beta = postgres_tenants

    def upload(name, version):
        content = f"ID,Name,Type\nsupplier,{name},Supplier\n".encode()
        return TabularImport(
            filename="synthetic-vendors.csv",
            content_base64=base64.b64encode(content).decode(),
            target="entities",
            mapping={"id": "ID", "name": "Name", "kind": "Type"},
            expected_version=version,
            provenance=source(),
        )

    staged = stage(store, alpha, upload("Before", 0), "analyst")
    applied = apply_import(store, alpha, staged["id"], "analyst")
    assert apply_import(store, alpha, staged["id"], "analyst") == applied
    first = store.snapshot(alpha)
    changed = stage(store, alpha, upload("After", 1), "analyst")
    apply_import(store, alpha, changed["id"], "analyst")
    assert store.snapshot(alpha).data.entities[0].name == "After"
    restored = rollback(store, alpha, changed["id"], "administrator", "Synthetic correction")
    assert restored["status"] == "rolled_back"
    assert store.snapshot(alpha).version == 3
    assert store.snapshot(alpha).data.entities[0].name == "Before"
    assert store.snapshot(alpha, version=2).data.entities[0].name == "After"
    assert store.snapshot(alpha, as_of=first.recorded_at).sha256 == first.sha256
    with pytest.raises(ValueError, match="unavailable"):
        apply_import(store, beta, staged["id"], "analyst")
    assert store.audit(alpha)["verification"]["valid"]


def test_postgres_concurrent_graph_updates_and_failed_transactions_preserve_audit(
    postgres_tenants,
):
    store, alpha, _ = postgres_tenants
    original = store.save(alpha, graph("Original"), "analyst", expected_version=0)
    original_audit = store.audit(alpha)
    with pytest.raises(RuntimeError, match="synthetic failure"):
        with tenant_transaction(store.engine, alpha) as session:
            org = store.organisation(session, alpha)
            store.save_in(session, org, graph("Rolled back"), "analyst", expected_version=1)
            session.flush()
            raise RuntimeError("synthetic failure after graph and audit flush")
    assert store.snapshot(alpha).sha256 == original.sha256
    assert store.audit(alpha) == original_audit

    barrier = Barrier(2)

    def writer(name):
        barrier.wait(timeout=5)
        try:
            return store.save(alpha, graph(name), "analyst", expected_version=1)
        except Conflict:
            return None

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(writer, ("First candidate", "Second candidate")))
    committed = [result for result in results if result is not None]
    assert len(committed) == 1
    assert store.snapshot(alpha).sha256 == committed[0].sha256
    assert store.snapshot(alpha).version == 2
    audit = store.audit(alpha)
    assert audit["verification"]["valid"]
    assert audit["verification"]["count"] == original_audit["verification"]["count"] + 1
    for table in ("graph_revisions", "platform_audit", "documents"):
        if table == "documents":
            store.add_document(alpha, "immutable", "Synthetic evidence", source(), "analyst")
        with pytest.raises(DBAPIError, match="append-only"):
            with tenant_transaction(store.engine, alpha) as session:
                session.execute(text(f"DELETE FROM {table}"))


def test_postgres_durable_plan_resumes_after_reconnect_and_requires_named_approval(
    postgres_tenants, monkeypatch
):
    from substrata.platform import agent_protocols

    store, alpha, beta = postgres_tenants
    monkeypatch.setenv("SUBSTRATA_ENV", "development")
    now = datetime.now(UTC)
    snapshot = store.save(alpha, generate("pharma", as_of=now), "analyst", expected_version=0)
    queued = enqueue(
        store,
        principal(alpha),
        JobInput(
            kind="agent_plan",
            idempotency_key="synthetic-review",
            payload={
                "plan": "risk_review",
                "arguments": {
                    "source_id": "upstream",
                    "severity": 0.8,
                    "as_of": now.isoformat(),
                    "max_depth": 4,
                    "graph_version": snapshot.version,
                },
            },
        ),
    )
    execute_tool = agent_protocols.execute_tool

    def unavailable_audit(*args, **kwargs):
        raise TimeoutError("Synthetic audit step outage")

    monkeypatch.setattr(agent_protocols, "execute_tool", unavailable_audit)
    assert run_next(store, principal(alpha))["status"] == "retry_scheduled"
    with tenant_transaction(store.engine, alpha) as session:
        record = session.get(WorkRecord, (alpha, queued["id"]))
        assert set(record.payload["checkpoints"]) == {"cascade_caller.assessment"}
        record.payload = {
            **record.payload,
            "retry_at": (now - timedelta(seconds=1)).isoformat(),
        }
    monkeypatch.setattr(agent_protocols, "execute_tool", execute_tool)

    # A fresh connection pool has no in-memory plan state to fall back on.
    restarted_engine = build_engine(store.engine.url.render_as_string(hide_password=False))
    try:
        restarted = PlatformStore(restarted_engine)
        completed = run_next(restarted, principal(alpha))
        assert completed["status"] == "succeeded"
        assert completed["payload"]["attempts"] == 2
        checkpoints = completed["payload"]["result"]["checkpoints"]
        assert checkpoints["compliance_audit.verification"]["valid"]
        assessments = list_records(restarted, alpha, kind="assessment")
        assert len(assessments) == 1
        assert assessments[0]["id"] == checkpoints["cascade_caller.assessment"]["assessment_id"]
        assert assessments[0]["payload"]["input_snapshot"]["sha256"] == snapshot.sha256
        assert assessments[0]["payload"]["report"]["impacts"]

        def measure(value, unit):
            return Measure(value=value, unit=unit, provenance=source())

        configure_policy(
            restarted,
            principal(alpha, "administrator", "admin"),
            Policy(
                currency="USD",
                spend_limit=measure(50000, "USD"),
                auto_approve_limit=measure(1000, "USD"),
                approval_sla=measure(24, "hour"),
            ),
        )
        proposed = propose(
            restarted,
            principal(alpha),
            ProposalInput(
                assessment_id=assessments[0]["id"],
                kind="buffer_buy",
                title="Synthetic buffer quote",
                cost=measure(15000, "USD"),
                duration=measure(7, "day"),
                rationale="Invented quote for a PostgreSQL workflow regression",
            ),
        )
        assert proposed["status"] == "pending"
        with pytest.raises(ValueError, match="different person"):
            decide(
                restarted,
                principal(alpha, "analyst", "approver"),
                proposed["id"],
                "approved",
                "Reviewed",
            )
        buyer = principal(alpha, "buyer", "approver")
        decide(restarted, buyer, proposed["id"], "approved", "Synthetic quote checked")
        preview = execute(restarted, buyer, proposed["id"])
        assert preview["status"] == "dry_run"
        assert execute(restarted, buyer, proposed["id"]) == preview
        assert list_records(restarted, beta, kind="assessment") == []
        with pytest.raises(ValueError, match="unavailable"):
            decide(
                restarted,
                principal(beta, "buyer", "approver"),
                proposed["id"],
                "approved",
                "Reviewed",
            )
        assert restarted.audit(alpha)["verification"]["valid"]
    finally:
        restarted_engine.dispose()


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
