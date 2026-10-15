"""Consistent PostgreSQL dumps and recovery into a new database only."""

import os
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from threading import Event, Timer

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from substrata.platform.backups import authenticated_backup, encrypt_backup
from substrata.platform.models import Base

FORMAT = "substrata-platform-database-v1"


def _terminate(process, expired):
    expired.set()
    if process.poll() is None:
        try:
            process.kill()
        except OSError:
            pass


def _manifest(connection, *, synthetic):
    privileged = connection.scalar(
        text("SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname = current_user")
    )
    if not privileged:
        raise ValueError("Whole-database backup needs a separate role that can read every RLS row.")
    heads = connection.execute(
        text(
            "SELECT o.tenant_id, o.version, o.audit_sequence, o.audit_head, g.sha256 "
            "FROM organisations o LEFT JOIN graph_revisions g "
            "ON g.tenant_id=o.tenant_id AND g.version=o.version ORDER BY o.tenant_id"
        )
    ).mappings()
    return {
        "format": FORMAT,
        "synthetic": synthetic,
        "created_at": datetime.now(UTC).isoformat(),
        "postgres_version": connection.scalar(text("SHOW server_version_num")),
        "schema_version": connection.scalar(
            text("SELECT version_num FROM platform_schema_version")
        ),
        "tenant_heads": {
            row["tenant_id"]: {
                "graph_version": row["version"],
                "graph_sha256": row["sha256"],
                "audit_sequence": row["audit_sequence"],
                "audit_head": row["audit_head"],
            }
            for row in heads
        },
        "table_counts": {
            name: connection.scalar(text(f"SELECT count(*) FROM {name}"))
            for name in Base.metadata.tables
        },
    }


def backup_database(
    engine,
    destination: Path,
    key: bytes,
    dump_command,
    *,
    environment=None,
    synthetic=False,
    timeout=300,
):
    """dump_command(snapshot_id) returns trusted argv, never a shell command.

    Hold an exported REPEATABLE READ snapshot so the encrypted manifest's heads
    and pg_dump's rows describe the same committed state during concurrent writes.
    """
    if engine.dialect.name != "postgresql":
        raise ValueError("Platform recovery tooling requires PostgreSQL.")
    destination = Path(destination).absolute()
    if destination.exists():
        raise FileExistsError(
            "Backup artifact already exists; existing evidence is never overwritten."
        )
    owned = False
    with engine.connect().execution_options(isolation_level="REPEATABLE READ") as connection:
        with connection.begin():
            snapshot = connection.scalar(text("SELECT pg_export_snapshot()"))
            manifest = _manifest(connection, synthetic=synthetic)
            process = subprocess.Popen(
                dump_command(snapshot),
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            expired = Event()
            timer = Timer(timeout, _terminate, args=(process, expired))
            timer.daemon = True
            timer.start()
            try:
                result = encrypt_backup(process.stdout, destination, key, manifest)
                owned = True
                if process.wait(timeout=5) != 0 or expired.is_set():
                    raise ValueError("pg_dump failed or timed out; no usable backup was created.")
            except BaseException:
                if owned:
                    destination.unlink(missing_ok=True)
                raise
            finally:
                timer.cancel()
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=5)
                process.stdout.close()
    return {**result, "manifest": manifest}


def restore_database(
    engine,
    source: Path,
    key: bytes,
    database: str,
    restore_command,
    *,
    environment=None,
    timeout=300,
):
    """Authenticate first, create a fresh database, then transactionally pg_restore.

    Never DROP or overwrite a database. A failed restore leaves the newly created
    database for inspection; pg_restore uses one transaction and exits on error.
    """
    if engine.dialect.name != "postgresql" or not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", database):
        raise ValueError("Recovery requires PostgreSQL and a new lowercase ASCII database name.")
    with authenticated_backup(source, key) as (verified, restore_to):
        manifest = verified["manifest"]
        if manifest.get("format") != FORMAT:
            raise ValueError("Authenticated archive is not a supported platform database backup.")
        quoted = engine.dialect.identifier_preparer.quote(database)
        try:
            with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
                connection.exec_driver_sql(f"CREATE DATABASE {quoted} TEMPLATE template0")
        except DBAPIError as error:
            if getattr(error.orig, "sqlstate", None) == "42P04":
                raise ValueError(
                    "Recovery database already exists; it will never be overwritten."
                ) from None
            raise ValueError(
                "Could not create the new recovery database; check administrator permissions."
            ) from None
        process = subprocess.Popen(
            [
                *restore_command(database),
                "--exit-on-error",
                "--single-transaction",
                "--no-owner",
                "--no-privileges",
            ],
            env=environment,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        expired = Event()
        timer = Timer(timeout, _terminate, args=(process, expired))
        timer.daemon = True
        timer.start()
        try:
            restore_to(process.stdin)
            process.stdin.close()
            if process.wait(timeout=timeout) != 0 or expired.is_set():
                raise ValueError(
                    "pg_restore failed or timed out; inspect the new database before use."
                )
        finally:
            timer.cancel()
            if not process.stdin.closed:
                process.stdin.close()
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)
    return {**verified, "database": database}


def client_environment(url, *, database=None):
    """libpq connection settings in child environment; passwords never enter argv."""
    values = {**os.environ}
    # A host's libpq defaults (including PGHOSTADDR or a weaker PGSSLMODE)
    # must not redirect or weaken the explicitly configured backup connection.
    for key in list(values):
        if key.startswith("PG"):
            values.pop(key)
    values.update(
        {
            "PGHOST": url.host or "localhost",
            "PGPORT": str(url.port or 5432),
            "PGUSER": url.username or "postgres",
            "PGDATABASE": database or url.database,
            "PGCONNECT_TIMEOUT": "10",
        }
    )
    if url.password:
        values["PGPASSWORD"] = url.password
    for option in ("sslmode", "sslrootcert", "sslcert", "sslkey"):
        if option in url.query:
            values["PG" + option.upper()] = url.query[option]
    return values
