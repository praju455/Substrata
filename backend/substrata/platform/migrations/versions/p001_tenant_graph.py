"""Tenant-scoped immutable snapshots, documents and audit records."""

import sqlalchemy as sa
from alembic import op

revision = "p001_tenant_graph"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "organisations",
        sa.Column("tenant_id", sa.String(96), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("audit_sequence", sa.Integer, nullable=False),
        sa.Column("audit_head", sa.String(64), nullable=False),
        sa.Column("policy", sa.JSON, nullable=False),
    )
    op.create_table(
        "graph_revisions",
        sa.Column(
            "tenant_id", sa.String(96), sa.ForeignKey("organisations.tenant_id"), primary_key=True
        ),
        sa.Column("version", sa.Integer, primary_key=True),
        sa.Column("recorded_at", sa.DateTime, nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
    )
    op.create_index("ix_graph_revisions_recorded_at", "graph_revisions", ["recorded_at"])
    op.create_table(
        "platform_audit",
        sa.Column(
            "tenant_id", sa.String(96), sa.ForeignKey("organisations.tenant_id"), primary_key=True
        ),
        sa.Column("sequence", sa.Integer, primary_key=True),
        sa.Column("previous_hash", sa.String(64), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("event_type", sa.String(96), nullable=False),
        sa.Column("actor", sa.String(256), nullable=False),
        sa.Column("timestamp", sa.DateTime, nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
    )
    op.create_table(
        "documents",
        sa.Column(
            "tenant_id", sa.String(96), sa.ForeignKey("organisations.tenant_id"), primary_key=True
        ),
        sa.Column("id", sa.String(96), primary_key=True),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("provenance", sa.JSON, nullable=False),
    )
    dialect = op.get_bind().dialect.name
    for table in ("organisations", "graph_revisions", "platform_audit", "documents"):
        if dialect == "postgresql":
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
            op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
            predicate = "tenant_id = current_setting('substrata.tenant_id', true)"
            op.execute(
                f"CREATE POLICY tenant_isolation ON {table} USING ({predicate}) "
                f"WITH CHECK ({predicate})"
            )
    if dialect == "postgresql":
        op.execute("""CREATE FUNCTION substrata_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
                      BEGIN RAISE EXCEPTION 'Record is append-only'; END; $$""")
    for table in ("graph_revisions", "platform_audit", "documents"):
        if dialect == "sqlite":
            for operation in ("UPDATE", "DELETE"):
                op.execute(
                    f"CREATE TRIGGER {table}_no_{operation.lower()} BEFORE {operation} "
                    f"ON {table} BEGIN SELECT RAISE(ABORT, 'Record is append-only'); END"
                )
        else:
            op.execute(
                f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} "
                "FOR EACH ROW EXECUTE FUNCTION substrata_immutable()"
            )


def downgrade():
    for table in ("documents", "platform_audit", "graph_revisions", "organisations"):
        op.drop_table(table)
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP FUNCTION substrata_immutable()")
