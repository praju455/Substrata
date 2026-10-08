"""Add versioned synthetic graph entities and evidence provenance."""

import sqlalchemy as sa
from alembic import op

revision = "0002_graph_provenance"
down_revision = "0001_database_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "graph_nodes",
        sa.Column("id", sa.String(length=96), nullable=False),
        sa.Column("graph_version", sa.Integer(), nullable=False),
        sa.Column("node_type", sa.String(length=24), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("normalized_name", sa.String(length=256), nullable=False),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("synthetic", sa.Boolean(), server_default="1", nullable=False),
        sa.CheckConstraint(
            "json_type(attributes) = 'object' AND "
            "json_extract(attributes, '$.node_type') IS node_type",
            name=op.f("ck_graph_nodes_attribute_type"),
        ),
        sa.CheckConstraint(
            "node_type IN ('Product','Component','SupplierSite','Plant','Region',"
            "'Event','AlternativeSupplier')",
            name=op.f("ck_graph_nodes_node_type"),
        ),
        sa.CheckConstraint("graph_version >= 1", name=op.f("ck_graph_nodes_positive_version")),
        sa.CheckConstraint(
            "length(trim(id)) > 0 AND length(trim(name)) > 0",
            name=op.f("ck_graph_nodes_nonempty_labels"),
        ),
        sa.CheckConstraint(
            "length(trim(normalized_name)) > 0", name=op.f("ck_graph_nodes_normalized_name")
        ),
        sa.CheckConstraint("synthetic = 1", name=op.f("ck_graph_nodes_synthetic_only")),
        sa.PrimaryKeyConstraint("id", "graph_version", name=op.f("pk_graph_nodes")),
        sa.UniqueConstraint("id", "graph_version", "node_type", name=op.f("uq_graph_nodes_id")),
    )
    op.create_index(
        "ix_graph_nodes_type_name", "graph_nodes", ["node_type", "normalized_name"], unique=False
    )
    op.create_table(
        "source_snapshots",
        sa.Column("id", sa.String(length=96), nullable=False),
        sa.Column("source_uri", sa.Text(), nullable=False),
        sa.Column("source_kind", sa.String(length=24), nullable=False),
        sa.Column("observed_at", sa.DateTime(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("permitted_excerpt", sa.Text(), nullable=False),
        sa.Column("license_note", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "length(content_sha256) = 64 AND content_sha256 NOT GLOB '*[^0-9a-f]*'",
            name=op.f("ck_source_snapshots_sha256"),
        ),
        sa.CheckConstraint(
            "source_kind IN ('synthetic','public_context')",
            name=op.f("ck_source_snapshots_source_kind"),
        ),
        sa.CheckConstraint("length(trim(id)) > 0", name=op.f("ck_source_snapshots_nonempty_id")),
        sa.CheckConstraint(
            "length(trim(source_uri)) > 0 AND length(trim(license_note)) > 0 "
            "AND length(trim(permitted_excerpt)) > 0",
            name=op.f("ck_source_snapshots_source_provenance"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_snapshots")),
    )
    op.create_table(
        "evidence_records",
        sa.Column("id", sa.String(length=96), nullable=False),
        sa.Column("source_snapshot_id", sa.String(length=96), nullable=False),
        sa.Column("claim", sa.Text(), nullable=False),
        sa.Column("reliability", sa.Float(), nullable=True),
        sa.Column("recency_days", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "length(trim(claim)) > 0", name=op.f("ck_evidence_records_nonempty_claim")
        ),
        sa.CheckConstraint("length(trim(id)) > 0", name=op.f("ck_evidence_records_nonempty_id")),
        sa.CheckConstraint(
            "recency_days >= 0", name=op.f("ck_evidence_records_recency_nonnegative")
        ),
        sa.CheckConstraint(
            "reliability >= 0 AND reliability <= 1",
            name=op.f("ck_evidence_records_reliability_range"),
        ),
        sa.ForeignKeyConstraint(
            ["source_snapshot_id"],
            ["source_snapshots.id"],
            name=op.f("fk_evidence_records_source_snapshot_id_source_snapshots"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evidence_records")),
    )
    op.create_index(
        "ix_evidence_records_snapshot", "evidence_records", ["source_snapshot_id"], unique=False
    )
    op.create_table(
        "graph_edges",
        sa.Column("id", sa.String(length=96), nullable=False),
        sa.Column("graph_version", sa.Integer(), nullable=False),
        sa.Column("from_node_id", sa.String(length=96), nullable=False),
        sa.Column("to_node_id", sa.String(length=96), nullable=False),
        sa.Column("from_node_type", sa.String(length=24), nullable=False),
        sa.Column("to_node_type", sa.String(length=24), nullable=False),
        sa.Column("edge_type", sa.String(length=24), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("primary_evidence_id", sa.String(length=96), nullable=True),
        sa.Column("last_verified", sa.DateTime(), nullable=True),
        sa.Column("valid_from", sa.DateTime(), nullable=False),
        sa.Column("valid_to", sa.DateTime(), nullable=True),
        sa.Column("share", sa.Float(), nullable=True),
        sa.Column("lead_time_days", sa.Float(), nullable=True),
        sa.Column("bom_quantity", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(length=48), nullable=True),
        sa.CheckConstraint(
            "(edge_type = 'SUPPLIES' AND from_node_type = 'SupplierSite' "
            "AND to_node_type = 'Component') OR "
            "(edge_type = 'USED_IN' AND from_node_type = 'Component' "
            "AND to_node_type IN ('Product','Plant')) OR "
            "(edge_type = 'LOCATED_IN' AND from_node_type IN "
            "('SupplierSite','Plant','Region') AND to_node_type = 'Region') OR "
            "(edge_type = 'OWNED_BY' AND from_node_type = 'SupplierSite' "
            "AND to_node_type = 'SupplierSite')",
            name=op.f("ck_graph_edges_typed_direction"),
        ),
        sa.CheckConstraint(
            "edge_type <> 'SUPPLIES' OR (share IS NOT NULL AND lead_time_days IS NOT NULL)",
            name=op.f("ck_graph_edges_supply_fields"),
        ),
        sa.CheckConstraint(
            "edge_type <> 'USED_IN' OR (bom_quantity IS NOT NULL AND bom_quantity > 0 "
            "AND unit IS NOT NULL AND length(trim(unit)) > 0)",
            name=op.f("ck_graph_edges_bom_fields"),
        ),
        sa.CheckConstraint(
            "edge_type = 'SUPPLIES' OR (share IS NULL AND lead_time_days IS NULL)",
            name=op.f("ck_graph_edges_supply_field_scope"),
        ),
        sa.CheckConstraint(
            "edge_type = 'USED_IN' OR (bom_quantity IS NULL AND unit IS NULL)",
            name=op.f("ck_graph_edges_bom_field_scope"),
        ),
        sa.CheckConstraint(
            "status <> 'confirmed' OR last_verified IS NOT NULL",
            name=op.f("ck_graph_edges_confirmed_time"),
        ),
        sa.CheckConstraint(
            "status <> 'inferred' OR primary_evidence_id IS NOT NULL",
            name=op.f("ck_graph_edges_inferred_evidence"),
        ),
        sa.CheckConstraint(
            "status IN ('declared','inferred','confirmed','rejected','expired')",
            name=op.f("ck_graph_edges_status"),
        ),
        sa.CheckConstraint("bom_quantity > 0", name=op.f("ck_graph_edges_bom_quantity_positive")),
        sa.CheckConstraint(
            "lead_time_days <= 1.7976931348623157e308 AND bom_quantity <= 1.7976931348623157e308",
            name=op.f("ck_graph_edges_finite_quantities"),
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1", name=op.f("ck_graph_edges_confidence_range")
        ),
        sa.CheckConstraint(
            "from_node_id <> to_node_id", name=op.f("ck_graph_edges_distinct_endpoints")
        ),
        sa.CheckConstraint("graph_version >= 1", name=op.f("ck_graph_edges_positive_version")),
        sa.CheckConstraint(
            "lead_time_days >= 0", name=op.f("ck_graph_edges_lead_time_nonnegative")
        ),
        sa.CheckConstraint("length(trim(id)) > 0", name=op.f("ck_graph_edges_nonempty_id")),
        sa.CheckConstraint("share >= 0 AND share <= 1", name=op.f("ck_graph_edges_share_range")),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to > valid_from", name=op.f("ck_graph_edges_validity_order")
        ),
        sa.ForeignKeyConstraint(
            ["from_node_id", "graph_version", "from_node_type"],
            ["graph_nodes.id", "graph_nodes.graph_version", "graph_nodes.node_type"],
            name=op.f("fk_graph_edges_from_node_id_graph_nodes"),
        ),
        sa.ForeignKeyConstraint(
            ["primary_evidence_id"],
            ["evidence_records.id"],
            name=op.f("fk_graph_edges_primary_evidence_id_evidence_records"),
        ),
        sa.ForeignKeyConstraint(
            ["to_node_id", "graph_version", "to_node_type"],
            ["graph_nodes.id", "graph_nodes.graph_version", "graph_nodes.node_type"],
            name=op.f("fk_graph_edges_to_node_id_graph_nodes"),
        ),
        sa.PrimaryKeyConstraint("id", "graph_version", name=op.f("pk_graph_edges")),
        sa.UniqueConstraint(
            "from_node_id",
            "to_node_id",
            "edge_type",
            "valid_from",
            "graph_version",
            name=op.f("uq_graph_edges_from_node_id"),
        ),
    )
    op.create_index(
        "ix_graph_edges_path",
        "graph_edges",
        ["from_node_id", "to_node_id", "edge_type", "valid_from"],
        unique=False,
    )
    op.create_index(
        "ix_graph_edges_review", "graph_edges", ["status", "last_verified"], unique=False
    )
    op.create_table(
        "edge_evidence",
        sa.Column("edge_id", sa.String(length=96), nullable=False),
        sa.Column("graph_version", sa.Integer(), nullable=False),
        sa.Column("evidence_id", sa.String(length=96), nullable=False),
        sa.Column("stance", sa.String(length=16), server_default="supports", nullable=False),
        sa.CheckConstraint(
            "stance IN ('supports','contradicts')", name=op.f("ck_edge_evidence_stance")
        ),
        sa.ForeignKeyConstraint(
            ["edge_id", "graph_version"],
            ["graph_edges.id", "graph_edges.graph_version"],
            name=op.f("fk_edge_evidence_edge_id_graph_edges"),
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["evidence_records.id"],
            name=op.f("fk_edge_evidence_evidence_id_evidence_records"),
        ),
        sa.PrimaryKeyConstraint(
            "edge_id", "graph_version", "evidence_id", name=op.f("pk_edge_evidence")
        ),
    )
    # A primary citation guarantees every inferred edge has an evidence link,
    # without circular foreign keys or an ordering requirement on callers.
    op.execute("""
        CREATE TRIGGER graph_edge_primary_insert AFTER INSERT ON graph_edges
        WHEN NEW.primary_evidence_id IS NOT NULL
        BEGIN
            INSERT INTO edge_evidence (edge_id, graph_version, evidence_id, stance)
            VALUES (NEW.id, NEW.graph_version, NEW.primary_evidence_id, 'supports');
        END
    """)
    op.execute("""
        CREATE TRIGGER graph_edge_primary_update
        AFTER UPDATE OF primary_evidence_id ON graph_edges
        WHEN NEW.primary_evidence_id IS NOT NULL
        BEGIN
            INSERT INTO edge_evidence (edge_id, graph_version, evidence_id, stance)
            VALUES (NEW.id, NEW.graph_version, NEW.primary_evidence_id, 'supports')
            ON CONFLICT (edge_id, graph_version, evidence_id) DO NOTHING;
            SELECT CASE WHEN EXISTS (
                SELECT 1 FROM edge_evidence
                WHERE edge_id = NEW.id AND graph_version = NEW.graph_version
                    AND evidence_id = NEW.primary_evidence_id AND stance <> 'supports'
            ) THEN RAISE(ABORT, 'Primary evidence must support the edge') END;
        END
    """)
    op.execute("""
        CREATE TRIGGER edge_primary_evidence_delete BEFORE DELETE ON edge_evidence
        WHEN EXISTS (
            SELECT 1 FROM graph_edges WHERE id = OLD.edge_id
                AND graph_version = OLD.graph_version AND primary_evidence_id = OLD.evidence_id
        )
        BEGIN
            SELECT RAISE(ABORT, 'Cannot remove primary edge evidence');
        END
    """)
    op.execute("""
        CREATE TRIGGER edge_primary_evidence_update BEFORE UPDATE ON edge_evidence
        WHEN EXISTS (
            SELECT 1 FROM graph_edges WHERE id = OLD.edge_id
                AND graph_version = OLD.graph_version AND primary_evidence_id = OLD.evidence_id
        )
        BEGIN
            SELECT RAISE(ABORT, 'Cannot change primary edge evidence');
        END
    """)
    op.execute("""
        CREATE TRIGGER graph_edge_confirmation_gate BEFORE UPDATE OF status ON graph_edges
        WHEN NEW.status = 'confirmed' AND OLD.status <> 'confirmed'
        BEGIN
            SELECT RAISE(ABORT, 'Confirmation workflow is not implemented yet');
        END
    """)


def downgrade() -> None:
    for trigger in (
        "graph_edge_confirmation_gate",
        "edge_primary_evidence_update",
        "edge_primary_evidence_delete",
        "graph_edge_primary_update",
        "graph_edge_primary_insert",
    ):
        op.execute(f"DROP TRIGGER {trigger}")
    op.drop_table("edge_evidence")
    op.drop_index("ix_graph_edges_review", table_name="graph_edges")
    op.drop_index("ix_graph_edges_path", table_name="graph_edges")
    op.drop_table("graph_edges")
    op.drop_index("ix_evidence_records_snapshot", table_name="evidence_records")
    op.drop_table("evidence_records")
    op.drop_table("source_snapshots")
    op.drop_index("ix_graph_nodes_type_name", table_name="graph_nodes")
    op.drop_table("graph_nodes")
