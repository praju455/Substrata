"""Passage retrieval with pgvector, tenant policy and portable offline storage."""

import sqlalchemy as sa
from alembic import op

from substrata.platform.vector import Embedding

revision = "p003_document_vectors"
down_revision = "p002_work_records"
branch_labels = None
depends_on = None


def upgrade():
    postgres = op.get_bind().dialect.name == "postgresql"
    if postgres:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "document_chunks",
        sa.Column("tenant_id", sa.String(96), primary_key=True),
        sa.Column("document_id", sa.String(96), primary_key=True),
        sa.Column("position", sa.Integer, primary_key=True),
        sa.Column("start", sa.Integer, nullable=False),
        sa.Column("end", sa.Integer, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("embedding_model", sa.String(128), primary_key=True),
        sa.Column("embedding", Embedding(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id", "document_id"], ["documents.tenant_id", "documents.id"]
        ),
    )
    if postgres:
        op.execute("ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE document_chunks FORCE ROW LEVEL SECURITY")
        predicate = "tenant_id = current_setting('substrata.tenant_id', true)"
        op.execute(
            f"CREATE POLICY tenant_isolation ON document_chunks USING ({predicate}) "
            f"WITH CHECK ({predicate})"
        )
        op.execute(
            "CREATE INDEX document_chunks_cosine ON document_chunks "
            "USING hnsw (embedding vector_cosine_ops)"
        )


def downgrade():
    op.drop_table("document_chunks")
