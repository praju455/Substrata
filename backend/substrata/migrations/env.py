"""Alembic environment using the application's configured connection."""

from alembic import context

from substrata import (  # noqa: F401 -- register mapped metadata
    agent_models,
    erp_models,
    models,
    workflow_models,
)
from substrata.database import Base

connection = context.config.attributes.get("connection")
if connection is None:
    raise RuntimeError("Run migrations through python scripts/dev.py migrate.")

context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
with context.begin_transaction():
    context.run_migrations()
