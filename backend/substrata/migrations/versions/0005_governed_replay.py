"""Versioned prototype schema: 0005_governed_replay."""

import sqlalchemy as sa
from alembic import op

revision = "0005_governed_replay"
down_revision = "0004_mapper_evaluation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("sequence", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("previous_hash", sa.String(length=64), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=48), nullable=False),
        sa.Column("actor", sa.String(length=96), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("sequence", name=op.f("pk_audit_events")),
    )
    op.create_table(
        "demo_state",
        sa.Column("id", sa.String(length=24), nullable=False),
        sa.Column("generation", sa.String(length=48), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_demo_state")),
    )
    op.create_table(
        "events",
        sa.Column("id", sa.String(length=96), nullable=False),
        sa.Column("event_type", sa.String(length=48), nullable=False),
        sa.Column("observed_at", sa.DateTime(), nullable=False),
        sa.Column("ingested_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=48), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_events")),
    )
    op.create_table(
        "stream_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_type", sa.String(length=48), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stream_events")),
    )
    op.create_table(
        "event_entity_matches",
        sa.Column("event_id", sa.String(length=96), nullable=False),
        sa.Column("node_id", sa.String(length=96), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("method", sa.String(length=48), nullable=False),
        sa.ForeignKeyConstraint(
            ["event_id"], ["events.id"], name=op.f("fk_event_entity_matches_event_id_events")
        ),
        sa.PrimaryKeyConstraint("event_id", "node_id", name=op.f("pk_event_entity_matches")),
    )
    op.create_table(
        "scenarios",
        sa.Column("id", sa.String(length=96), nullable=False),
        sa.Column("event_id", sa.String(length=96), nullable=False),
        sa.Column("status", sa.String(length=48), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["event_id"], ["events.id"], name=op.f("fk_scenarios_event_id_events")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scenarios")),
    )
    op.create_table(
        "action_proposals",
        sa.Column("id", sa.String(length=96), nullable=False),
        sa.Column("scenario_id", sa.String(length=96), nullable=False),
        sa.Column("kind", sa.String(length=48), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("cost", sa.Float(), nullable=False),
        sa.Column("duration_days", sa.Float(), nullable=False),
        sa.Column("risk", sa.Float(), nullable=False),
        sa.Column("rank_score", sa.Float(), nullable=False),
        sa.Column("policy", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=48), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "cost >= 0 AND cost <= 1.7976931348623157e308", name=op.f("ck_action_proposals_cost")
        ),
        sa.ForeignKeyConstraint(
            ["scenario_id"],
            ["scenarios.id"],
            name=op.f("fk_action_proposals_scenario_id_scenarios"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_action_proposals")),
    )
    op.create_table(
        "impact_results",
        sa.Column("scenario_id", sa.String(length=96), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["scenario_id"], ["scenarios.id"], name=op.f("fk_impact_results_scenario_id_scenarios")
        ),
        sa.PrimaryKeyConstraint("scenario_id", name=op.f("pk_impact_results")),
    )
    op.create_table(
        "approval_queue",
        sa.Column("action_id", sa.String(length=96), nullable=False),
        sa.Column("snapshot_sha256", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.ForeignKeyConstraint(
            ["action_id"],
            ["action_proposals.id"],
            name=op.f("fk_approval_queue_action_id_action_proposals"),
        ),
        sa.PrimaryKeyConstraint("action_id", name=op.f("pk_approval_queue")),
    )
    op.create_table(
        "approval_decisions",
        sa.Column("action_id", sa.String(length=96), nullable=False),
        sa.Column("actor", sa.String(length=96), nullable=False),
        sa.Column("role", sa.String(length=48), nullable=False),
        sa.Column("decision", sa.String(length=24), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("decided_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["action_id"],
            ["approval_queue.action_id"],
            name=op.f("fk_approval_decisions_action_id_approval_queue"),
        ),
        sa.PrimaryKeyConstraint("action_id", name=op.f("pk_approval_decisions")),
    )

    op.execute("""
        CREATE TRIGGER audit_no_update BEFORE UPDATE ON audit_events
        BEGIN SELECT RAISE(ABORT, 'Audit events are append-only'); END
    """)
    op.execute("""
        CREATE TRIGGER audit_no_delete BEFORE DELETE ON audit_events
        BEGIN SELECT RAISE(ABORT, 'Audit events are append-only'); END
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER audit_no_update")
    op.execute("DROP TRIGGER audit_no_delete")
    op.drop_table("approval_decisions")
    op.drop_table("approval_queue")
    op.drop_table("impact_results")
    op.drop_table("action_proposals")
    op.drop_table("scenarios")
    op.drop_table("event_entity_matches")
    op.drop_table("stream_events")
    op.drop_table("events")
    op.drop_table("demo_state")
    op.drop_table("audit_events")
