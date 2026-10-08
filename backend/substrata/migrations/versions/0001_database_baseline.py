"""Establish schema history before domain tables are introduced."""

revision = "0001_database_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Alembic creates its version table; no domain schema exists yet."""


def downgrade() -> None:
    """No domain schema to remove in the baseline."""
