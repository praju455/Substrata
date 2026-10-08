"""Explicit SQLite setup and transaction boundaries; importing creates no files."""

from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path
from sqlite3 import Connection

from alembic import command
from alembic.config import Config
from sqlalchemy import URL, Engine, MetaData, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session


class Base(DeclarativeBase):
    """Shared metadata for domain models added in subsequent checkpoints."""

    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(table_name)s_%(column_0_name)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


def build_engine(path: Path) -> Engine:
    """Prepare a file-backed database; the first connection configures SQLite."""
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        URL.create("sqlite+pysqlite", database=str(path)),
        connect_args={"autocommit": False, "timeout": 5.0},
    )

    @event.listens_for(engine, "connect")
    def configure_connection(connection: Connection, _record: object) -> None:
        # PRAGMAs must run outside a transaction. Python >=3.12 supports autocommit.
        previous = connection.autocommit
        connection.autocommit = True
        try:
            with closing(connection.cursor()) as cursor:
                cursor.execute("PRAGMA busy_timeout=5000")
                cursor.execute("PRAGMA foreign_keys=ON")
                mode = cursor.execute("PRAGMA journal_mode=WAL").fetchone()[0]
                if mode.lower() != "wal":
                    raise RuntimeError("SQLite could not enable WAL mode.")
        finally:
            connection.autocommit = previous

    return engine


@contextmanager
def transaction(engine: Engine) -> Iterator[Session]:
    """Commit a complete unit of work, or roll it back and close on failure."""
    with Session(engine, expire_on_commit=False) as session, session.begin():
        yield session


def upgrade_database(engine: Engine) -> None:
    """Apply checked-in migrations to head without resetting existing records."""
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).parent / "migrations"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
