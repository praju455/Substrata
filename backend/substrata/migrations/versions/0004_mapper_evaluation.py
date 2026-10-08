"""Versioned prototype schema: 0004_mapper_evaluation."""

import sqlalchemy as sa
from alembic import op

revision = "0004_mapper_evaluation"
down_revision = "0003_synthetic_erp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(length=96), nullable=False),
        sa.Column("agent", sa.String(length=48), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("provider", sa.String(length=96), nullable=False),
        sa.Column("model", sa.String(length=96), nullable=False),
        sa.Column("prompt_version", sa.String(length=48), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("schema_valid", sa.Boolean(), nullable=False),
        sa.Column("output", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_agent_runs")),
    )
    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.String(length=96), nullable=False),
        sa.Column("dataset_version", sa.String(length=96), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evaluation_runs")),
    )
    op.create_table(
        "evaluation_examples",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("evaluation_run_id", sa.String(length=96), nullable=False),
        sa.Column("edge_id", sa.String(length=96), nullable=False),
        sa.Column("expected", sa.Boolean(), nullable=False),
        sa.Column("predicted", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["evaluation_run_id"],
            ["evaluation_runs.id"],
            name=op.f("fk_evaluation_examples_evaluation_run_id_evaluation_runs"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evaluation_examples")),
    )
    op.create_table(
        "evaluation_metrics",
        sa.Column("evaluation_run_id", sa.String(length=96), nullable=False),
        sa.Column("name", sa.String(length=96), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(
            ["evaluation_run_id"],
            ["evaluation_runs.id"],
            name=op.f("fk_evaluation_metrics_evaluation_run_id_evaluation_runs"),
        ),
        sa.PrimaryKeyConstraint("evaluation_run_id", "name", name=op.f("pk_evaluation_metrics")),
    )
    op.create_table(
        "tool_calls",
        sa.Column("id", sa.String(length=96), nullable=False),
        sa.Column("agent_run_id", sa.String(length=96), nullable=False),
        sa.Column("tool", sa.String(length=96), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["agent_run_id"], ["agent_runs.id"], name=op.f("fk_tool_calls_agent_run_id_agent_runs")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tool_calls")),
    )
    op.create_table(
        "confirmation_requests",
        sa.Column("id", sa.String(length=96), nullable=False),
        sa.Column("edge_id", sa.String(length=96), nullable=False),
        sa.Column("graph_version", sa.Integer(), nullable=False),
        sa.Column("evidence_id", sa.String(length=96), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("candidate", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="pending", nullable=False),
        sa.CheckConstraint(
            "status IN ('pending','confirmed','rejected')",
            name=op.f("ck_confirmation_requests_status"),
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["evidence_records.id"],
            name=op.f("fk_confirmation_requests_evidence_id_evidence_records"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_confirmation_requests")),
        sa.UniqueConstraint("edge_id", name=op.f("uq_confirmation_requests_edge_id")),
    )
    op.create_table(
        "confirmation_responses",
        sa.Column("request_id", sa.String(length=96), nullable=False),
        sa.Column("decision", sa.String(length=24), nullable=False),
        sa.Column("responder", sa.String(length=96), nullable=False),
        sa.Column("responded_at", sa.DateTime(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "decision IN ('confirmed','rejected')", name=op.f("ck_confirmation_responses_decision")
        ),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["confirmation_requests.id"],
            name=op.f("fk_confirmation_responses_request_id_confirmation_requests"),
        ),
        sa.PrimaryKeyConstraint("request_id", name=op.f("pk_confirmation_responses")),
    )

    op.execute("DROP TRIGGER graph_edge_confirmation_gate")
    op.execute("""
        CREATE TRIGGER graph_edge_confirmation_gate BEFORE UPDATE OF status ON graph_edges
        WHEN NEW.status = 'confirmed' AND OLD.status <> 'confirmed' AND NOT EXISTS (
            SELECT 1 FROM confirmation_requests r
            JOIN confirmation_responses s ON s.request_id = r.id
            WHERE r.edge_id = NEW.id AND r.graph_version = NEW.graph_version
                AND r.evidence_id = NEW.primary_evidence_id AND s.decision = 'confirmed'
        )
        BEGIN
            SELECT RAISE(ABORT, 'Confirmation workflow response required');
        END
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER graph_edge_confirmation_gate")
    op.execute("""
        CREATE TRIGGER graph_edge_confirmation_gate BEFORE UPDATE OF status ON graph_edges
        WHEN NEW.status = 'confirmed' AND OLD.status <> 'confirmed'
        BEGIN
            SELECT RAISE(ABORT, 'Confirmation workflow is not implemented yet');
        END
    """)
    op.drop_table("confirmation_responses")
    op.drop_table("confirmation_requests")
    op.drop_table("tool_calls")
    op.drop_table("evaluation_metrics")
    op.drop_table("evaluation_examples")
    op.drop_table("evaluation_runs")
    op.drop_table("agent_runs")
