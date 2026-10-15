"""Restore an encrypted synthetic backup using two disposable Docker databases."""

import json
import os
import secrets
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def provision(engine, database, password):
    # All values are generated internally: fixed role, ASCII database, hex password.
    role = "substrata_recovery_runtime"
    with engine.begin() as connection:
        connection.exec_driver_sql(
            f"CREATE ROLE {role} LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD '{password}'"
        )
        connection.exec_driver_sql(f"GRANT CONNECT ON DATABASE {database} TO {role}")
        connection.exec_driver_sql(f"GRANT USAGE ON SCHEMA public TO {role}")
        connection.exec_driver_sql(
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {role}"
        )
        connection.exec_driver_sql(
            f"GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO {role}"
        )
    return role


def drill(directory):
    from sqlalchemy import select, text
    from sqlalchemy.exc import DBAPIError

    from substrata.platform.auth import Principal
    from substrata.platform.backup_ops import backup_database, restore_database
    from substrata.platform.backups import create_key
    from substrata.platform.database import build_engine, migrate, tenant_transaction
    from substrata.platform.evidence import index_documents, retrieve
    from substrata.platform.jobs import JobInput, enqueue, run_next
    from substrata.platform.models import Base, Document, WorkRecord
    from substrata.platform.providers import LexicalEmbeddings
    from substrata.platform.records import list_records
    from substrata.platform.seeds import generate
    from substrata.platform.store import PlatformStore

    if __package__:
        from .docker_postgres import DisposablePostgres
    else:
        from docker_postgres import DisposablePostgres

    engines = []

    def engine(url):
        value = build_engine(url)
        engines.append(value)
        return value

    checks = {}
    now = datetime.now(UTC)
    password = secrets.token_hex(24)
    embedder = LexicalEmbeddings()
    with DisposablePostgres() as source, DisposablePostgres() as target:
        try:
            admin = engine(source.url())
            migrate(admin)
            role = provision(admin, "substrata_test", password)
            store = PlatformStore(engine(source.url(user=role, password=password)))
            snapshots = {}
            for tenant, industry in (("alpha", "automotive"), ("beta", "food")):
                store.provision(tenant, f"Synthetic {industry}", "drill-admin")
                data = generate(industry, as_of=now)
                first = store.save(tenant, data, "drill-analyst", expected_version=0)
                data.entities[0] = data.entities[0].model_copy(
                    update={"name": data.entities[0].name + " revision two"}
                )
                second = store.save(tenant, data, "drill-analyst", expected_version=1)
                snapshots[tenant] = (first.sha256, second.sha256)
                store.add_document(
                    tenant,
                    "filing",
                    f"Synthetic evidence for {tenant}.",
                    data.entities[0].provenance,
                    "drill-analyst",
                )
                index_documents(
                    store,
                    Principal(subject="drill-analyst", tenant_id=tenant, roles={"analyst"}),
                    embedder,
                )
            actor = Principal(subject="drill-analyst", tenant_id="alpha", roles={"analyst"})
            enqueue(
                store,
                actor,
                JobInput(
                    kind="assessment",
                    idempotency_key="recovery",
                    payload={
                        "graph_version": 2,
                        "assessment": {
                            "source_id": "upstream",
                            "severity": 0.8,
                            "as_of": now.isoformat(),
                            "max_depth": 4,
                        },
                    },
                ),
            )
            key_file, artifact = directory / "key.secret", directory / "backup.enc"
            create_key(key_file)
            key = key_file.read_bytes()

            def dump(snapshot):
                # Commit after the manifest snapshot. The dump must retain version 2.
                data = store.snapshot("alpha").data
                data.entities[0] = data.entities[0].model_copy(
                    update={"name": data.entities[0].name + " concurrent revision three"}
                )
                store.save("alpha", data, "drill-analyst", expected_version=2)
                return source.command(
                    "pg_dump",
                    "-U",
                    "postgres",
                    "-d",
                    "substrata_test",
                    "--format=custom",
                    "--no-owner",
                    "--no-privileges",
                    f"--snapshot={snapshot}",
                )

            started = time.monotonic()
            backup = backup_database(
                admin, artifact, key, dump, synthetic=True, environment=source.environment
            )
            backup_seconds = time.monotonic() - started
            target_admin = engine(target.url())

            def restore(name):
                return target.command("-i", "pg_restore", "-U", "postgres", "-d", name)

            corrupt = directory / "corrupt.enc"
            damaged = bytearray(artifact.read_bytes())
            damaged[-1] ^= 1
            corrupt.write_bytes(damaged)
            try:
                restore_database(
                    target_admin, corrupt, key, "rejected", restore, environment=target.environment
                )
                raise AssertionError("Corrupt backup was accepted.")
            except ValueError:
                with target_admin.connect() as connection:
                    assert not connection.scalar(
                        text("SELECT 1 FROM pg_database WHERE datname='rejected'")
                    )
            checks["tampering_rejected_before_database_creation"] = True
            started = time.monotonic()
            restored = restore_database(
                target_admin, artifact, key, "recovered", restore, environment=target.environment
            )
            restore_seconds = time.monotonic() - started
            assert restored["manifest"] == backup["manifest"]
            try:
                restore_database(
                    target_admin,
                    artifact,
                    key,
                    "recovered",
                    restore,
                    environment=target.environment,
                )
                raise AssertionError("Existing database was overwritten.")
            except ValueError as error:
                assert "already exists" in str(error)
            checks["existing_database_preserved"] = True
            recovered_admin = engine(target.url(database="recovered"))
            migrate(recovered_admin)
            migrate(recovered_admin)
            provision(recovered_admin, "recovered", password)
            recovered = PlatformStore(
                engine(target.url(database="recovered", user=role, password=password))
            )
            with recovered_admin.connect() as connection:
                for table, count in backup["manifest"]["table_counts"].items():
                    assert connection.scalar(text(f"SELECT count(*) FROM {table}")) == count
                    assert connection.execute(
                        text(
                            "SELECT relrowsecurity, relforcerowsecurity "
                            "FROM pg_class WHERE oid=to_regclass(:name)"
                        ),
                        {"name": f"public.{table}"},
                    ).one() == (True, True)
                assert set(backup["manifest"]["table_counts"]) == set(Base.metadata.tables)
            for tenant in snapshots:
                heads = backup["manifest"]["tenant_heads"][tenant]
                assert recovered.snapshot(tenant).version == heads["graph_version"] == 2
                for version, sha in enumerate(snapshots[tenant], 1):
                    assert recovered.snapshot(tenant, version=version).sha256 == sha
                assert recovered.audit(tenant, expected_head=heads["audit_head"])["verification"][
                    "valid"
                ]
                assert (
                    retrieve(recovered, tenant, "Synthetic evidence", embedder=embedder)[0]["text"]
                    == f"Synthetic evidence for {tenant}."
                )
                with tenant_transaction(recovered.engine, tenant) as session:
                    assert {row.tenant_id for row in session.scalars(select(Document))} == {tenant}
            assert store.snapshot("alpha").version == 3
            checks.update(
                snapshot_consistency_during_writes=True,
                graph_history_and_audit=True,
                table_counts_and_forced_rls=True,
                tenant_scoped_vector_retrieval=True,
            )
            try:
                with tenant_transaction(recovered.engine, "alpha") as session:
                    session.add(
                        WorkRecord(
                            tenant_id="beta",
                            id="forbidden",
                            kind="test",
                            status="ready",
                            created_at=now,
                            payload={},
                        )
                    )
                    session.flush()
                raise AssertionError("Cross-tenant write was accepted.")
            except DBAPIError:
                pass
            try:
                with tenant_transaction(recovered.engine, "alpha") as session:
                    session.execute(text("DELETE FROM platform_audit"))
                raise AssertionError("Audit deletion was accepted.")
            except DBAPIError:
                pass
            checks["cross_tenant_write_and_audit_delete_denied"] = True
            assert run_next(recovered, actor)["status"] == "succeeded"
            assert len(list_records(recovered, "alpha", kind="assessment")) == 1
            assert not list_records(recovered, "beta", kind="assessment")
            assert recovered.audit("alpha")["verification"]["valid"]
            checks["durable_job_resumed_after_restore"] = True
            return {
                "synthetic": True,
                "created_at": now.isoformat(),
                "checks": checks,
                "postgres_version": backup["manifest"]["postgres_version"],
                "schema_version": backup["manifest"]["schema_version"],
                "archive_bytes": restored["archive_bytes"],
                "encrypted_bytes": backup["encrypted_bytes"],
                "backup_seconds": round(backup_seconds, 3),
                "restore_seconds": round(restore_seconds, 3),
            }
        finally:
            for value in reversed(engines):
                value.dispose()


def main():
    if VENV.is_file() and Path(sys.executable).resolve() != VENV.resolve():
        return subprocess.run([str(VENV), str(Path(__file__).resolve())], cwd=ROOT).returncode
    # Only synthetic, owned databases are used; no live connectors or supplier contact.
    os.environ["SUBSTRATA_ENV"] = "development"
    output = (ROOT / "data/recovery-drills").resolve()
    output.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix="owned-", dir=output) as temporary:
            directory = Path(temporary).resolve()
            if not directory.is_relative_to(output):
                raise RuntimeError("Recovery temporary directory escaped the output area.")
            report = drill(directory)
        path = output / f"recovery-{uuid4().hex}.json"
        with path.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2)
        print(json.dumps(report, separators=(",", ":")))
        print(f"Recovery report: {path}")
        return 0
    except Exception as error:
        from pydantic import ValidationError

        if isinstance(error, ValidationError):
            print(
                json.dumps(
                    [
                        {"field": item["loc"], "type": item["type"]}
                        for item in error.errors(include_input=False, include_context=False)
                    ]
                ),
                file=sys.stderr,
            )
        print(
            f"Recovery drill failed ({type(error).__name__}); no live database was changed.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
