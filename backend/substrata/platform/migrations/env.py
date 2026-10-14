"""Portable platform migration history; never runs legacy SQLite migrations."""

from alembic import context

from substrata.platform.models import Base

connection = context.config.attributes["connection"]
context.configure(
    connection=connection,
    target_metadata=Base.metadata,
    version_table="platform_schema_version",
    compare_type=True,
)
with context.begin_transaction():
    context.run_migrations()
