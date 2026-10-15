"""Recovery must authenticate before writing and keep credentials out of argv."""

import io
import os
from types import SimpleNamespace

import pytest
from sqlalchemy.engine import make_url

from scripts.platform_backup import database_url
from substrata.platform.backup_ops import FORMAT, client_environment, restore_database
from substrata.platform.backups import encrypt_backup


@pytest.mark.parametrize("corrupt", [True, False])
def test_recovery_rejects_tampering_and_unsupported_manifest_before_database_access(
    tmp_path, corrupt
):
    key = os.urandom(32)
    path = tmp_path / "artifact.enc"
    encrypt_backup(
        io.BytesIO(b"PGDMPfixture"), path, key, {"format": FORMAT if corrupt else "unsupported"}
    )
    if corrupt:
        damaged = bytearray(path.read_bytes())
        damaged[-1] ^= 1
        path.write_bytes(damaged)

    class Untouched:
        dialect = SimpleNamespace(name="postgresql")

        def connect(self):
            pytest.fail("Unverified backup reached the database.")

    def restore_command(name):
        pytest.fail("Unverified backup launched a native restore.")

    with pytest.raises(ValueError):
        restore_database(Untouched(), path, key, "recovered", restore_command)


@pytest.mark.parametrize("name", ["existing;DROP DATABASE customer", "../database", "A", "a" * 64])
def test_recovery_rejects_unsafe_database_names_before_file_access(name):
    engine = SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))
    with pytest.raises(ValueError, match="lowercase ASCII"):
        restore_database(engine, "nonexistent", b"unused", name, None)


def test_client_credentials_use_environment_and_clear_inherited_overrides(monkeypatch):
    monkeypatch.setenv("PGPASSWORD", "old-secret")
    monkeypatch.setenv("PGSERVICE", "unexpected-service")
    monkeypatch.setenv("PGOPTIONS", "-c role=unexpected")
    monkeypatch.setenv("PGHOSTADDR", "192.0.2.1")
    monkeypatch.setenv("PGSSLMODE", "disable")
    url = make_url(
        "postgresql+psycopg://backup:private-password@db.example:5433/platform?sslmode=verify-full"
    )
    values = client_environment(url, database="recovered")
    assert values["PGPASSWORD"] == "private-password"
    assert values["PGDATABASE"] == "recovered"
    assert values["PGSSLMODE"] == "verify-full"
    assert values["PGHOST"] == "db.example"
    assert values["PGPORT"] == "5433"
    assert "PGSERVICE" not in values and "PGOPTIONS" not in values
    assert "PGHOSTADDR" not in values
    assert "PGPASSWORD" not in client_environment(
        make_url("postgresql+psycopg://backup@db/platform")
    )
    assert os.environ["PGPASSWORD"] == "old-secret"


def test_production_backup_requires_verified_tls(monkeypatch):
    monkeypatch.setenv("SUBSTRATA_ENV", "production")
    monkeypatch.setenv(
        "SUBSTRATA_BACKUP_DATABASE_URL", "postgresql+psycopg://backup:secret@db/platform"
    )
    with pytest.raises(ValueError, match="verify-full"):
        database_url("SUBSTRATA_BACKUP_DATABASE_URL")
    monkeypatch.setenv(
        "SUBSTRATA_BACKUP_DATABASE_URL",
        "postgresql+psycopg://backup:secret@db/platform?sslmode=verify-full",
    )
    assert database_url("SUBSTRATA_BACKUP_DATABASE_URL").query["sslmode"] == "verify-full"
