"""Tenant transactions and separate Alembic history for the portable platform."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from pydantic import TypeAdapter
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from substrata.database import build_engine as sqlite_engine
from substrata.platform.domain import Identifier


def build_engine(url: str) -> Engine:
    parsed = make_url(url)
    if parsed.get_backend_name() == "sqlite":
        if not parsed.database or parsed.database == ":memory:":
            raise ValueError("Use a file-backed SQLite database for offline platform tests.")
        return sqlite_engine(Path(parsed.database))
    if parsed.drivername != "postgresql+psycopg":
        raise ValueError("Platform database must use PostgreSQL/psycopg or offline SQLite.")
    return create_engine(parsed, pool_pre_ping=True, pool_size=10, max_overflow=10)


@contextmanager
def tenant_transaction(engine: Engine, tenant_id: str) -> Iterator[Session]:
    tenant_id = TypeAdapter(Identifier).validate_python(tenant_id)
    with Session(engine, expire_on_commit=False) as session, session.begin():
        session.info["tenant_id"] = tenant_id
        if engine.dialect.name == "postgresql":
            session.execute(
                text("SELECT set_config('substrata.tenant_id', :tenant, true)"),
                {"tenant": tenant_id},
            )
        yield session


def migrate(engine: Engine) -> None:
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).parent / "migrations"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
