"""Tenant-scoped workflow records for imports and human review."""

import sqlalchemy as sa
from alembic import op

revision = "p002_work_records"
down_revision = "p001_tenant_graph"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "work_records",
        sa.Column(
            "tenant_id", sa.String(96), sa.ForeignKey("organisations.tenant_id"), primary_key=True
        ),
        sa.Column("id", sa.String(96), primary_key=True),
        sa.Column("kind", sa.String(48), nullable=False),
        sa.Column("status", sa.String(48), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
    )
    op.create_index("ix_work_records_inbox", "work_records", ["tenant_id", "kind", "status"])
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE work_records ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE work_records FORCE ROW LEVEL SECURITY")
        predicate = "tenant_id = current_setting('substrata.tenant_id', true)"
        op.execute(
            f"CREATE POLICY tenant_isolation ON work_records USING ({predicate}) "
            f"WITH CHECK ({predicate})"
        )


def downgrade():
    op.drop_table("work_records")
