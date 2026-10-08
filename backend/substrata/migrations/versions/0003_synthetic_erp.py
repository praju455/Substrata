"""Versioned prototype schema: 0003_synthetic_erp."""

import sqlalchemy as sa
from alembic import op

revision = "0003_synthetic_erp"
down_revision = "0002_graph_provenance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "erp_datasets",
        sa.Column("id", sa.String(length=96), nullable=False),
        sa.Column("graph_version", sa.Integer(), nullable=False),
        sa.Column("inventory_snapshot_id", sa.String(length=96), nullable=False),
        sa.Column("as_of", sa.DateTime(), nullable=False),
        sa.Column("source_kind", sa.String(length=24), server_default="synthetic", nullable=False),
        sa.CheckConstraint(
            "source_kind = 'synthetic'", name=op.f("ck_erp_datasets_synthetic_only")
        ),
        sa.CheckConstraint("graph_version >= 1", name=op.f("ck_erp_datasets_graph_version")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_erp_datasets")),
        sa.UniqueConstraint(
            "inventory_snapshot_id", name=op.f("uq_erp_datasets_inventory_snapshot_id")
        ),
    )
    op.create_table(
        "bom_items",
        sa.Column("id", sa.String(length=96), nullable=False),
        sa.Column("dataset_version", sa.String(length=96), nullable=False),
        sa.Column("component_id", sa.String(length=96), nullable=False),
        sa.Column("product_id", sa.String(length=96), nullable=False),
        sa.Column("graph_version", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=48), nullable=False),
        sa.CheckConstraint("length(trim(unit)) > 0", name=op.f("ck_bom_items_unit")),
        sa.CheckConstraint(
            "quantity > 0 AND quantity <= 1.7976931348623157e308",
            name=op.f("ck_bom_items_quantity"),
        ),
        sa.ForeignKeyConstraint(
            ["component_id", "graph_version"],
            ["graph_nodes.id", "graph_nodes.graph_version"],
            name=op.f("fk_bom_items_component_id_graph_nodes"),
        ),
        sa.ForeignKeyConstraint(
            ["dataset_version"],
            ["erp_datasets.id"],
            name=op.f("fk_bom_items_dataset_version_erp_datasets"),
        ),
        sa.ForeignKeyConstraint(
            ["product_id", "graph_version"],
            ["graph_nodes.id", "graph_nodes.graph_version"],
            name=op.f("fk_bom_items_product_id_graph_nodes"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bom_items")),
    )
    op.create_table(
        "lead_times",
        sa.Column("dataset_version", sa.String(length=96), nullable=False),
        sa.Column("component_id", sa.String(length=96), nullable=False),
        sa.Column("graph_version", sa.Integer(), nullable=False),
        sa.Column("requalification_days", sa.Float(), nullable=True),
        sa.Column("provenance", sa.String(length=256), nullable=False),
        sa.CheckConstraint("length(trim(provenance)) > 0", name=op.f("ck_lead_times_provenance")),
        sa.CheckConstraint(
            "requalification_days >= 0 AND requalification_days <= 1.7976931348623157e308",
            name=op.f("ck_lead_times_requalification"),
        ),
        sa.ForeignKeyConstraint(
            ["component_id", "graph_version"],
            ["graph_nodes.id", "graph_nodes.graph_version"],
            name=op.f("fk_lead_times_component_id_graph_nodes"),
        ),
        sa.ForeignKeyConstraint(
            ["dataset_version"],
            ["erp_datasets.id"],
            name=op.f("fk_lead_times_dataset_version_erp_datasets"),
        ),
        sa.PrimaryKeyConstraint("dataset_version", "component_id", name=op.f("pk_lead_times")),
    )
    op.create_table(
        "plant_stock",
        sa.Column("dataset_version", sa.String(length=96), nullable=False),
        sa.Column("component_id", sa.String(length=96), nullable=False),
        sa.Column("plant_id", sa.String(length=96), nullable=False),
        sa.Column("graph_version", sa.Integer(), nullable=False),
        sa.Column("inventory_snapshot_id", sa.String(length=96), nullable=False),
        sa.Column("as_of", sa.DateTime(), nullable=False),
        sa.Column("on_hand", sa.Float(), nullable=True),
        sa.Column("daily_consumption", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(length=48), nullable=False),
        sa.CheckConstraint(
            "daily_consumption >= 0 AND daily_consumption <= 1.7976931348623157e308",
            name=op.f("ck_plant_stock_daily_consumption"),
        ),
        sa.CheckConstraint("length(trim(unit)) > 0", name=op.f("ck_plant_stock_unit")),
        sa.CheckConstraint(
            "on_hand >= 0 AND on_hand <= 1.7976931348623157e308",
            name=op.f("ck_plant_stock_on_hand"),
        ),
        sa.ForeignKeyConstraint(
            ["component_id", "graph_version"],
            ["graph_nodes.id", "graph_nodes.graph_version"],
            name=op.f("fk_plant_stock_component_id_graph_nodes"),
        ),
        sa.ForeignKeyConstraint(
            ["dataset_version"],
            ["erp_datasets.id"],
            name=op.f("fk_plant_stock_dataset_version_erp_datasets"),
        ),
        sa.ForeignKeyConstraint(
            ["plant_id", "graph_version"],
            ["graph_nodes.id", "graph_nodes.graph_version"],
            name=op.f("fk_plant_stock_plant_id_graph_nodes"),
        ),
        sa.PrimaryKeyConstraint(
            "dataset_version", "component_id", "plant_id", name=op.f("pk_plant_stock")
        ),
    )
    op.create_table(
        "vendor_master",
        sa.Column("id", sa.String(length=96), nullable=False),
        sa.Column("dataset_version", sa.String(length=96), nullable=False),
        sa.Column("supplier_site_id", sa.String(length=96), nullable=False),
        sa.Column("graph_version", sa.Integer(), nullable=False),
        sa.Column("vendor_name", sa.String(length=256), nullable=False),
        sa.ForeignKeyConstraint(
            ["dataset_version"],
            ["erp_datasets.id"],
            name=op.f("fk_vendor_master_dataset_version_erp_datasets"),
        ),
        sa.ForeignKeyConstraint(
            ["supplier_site_id", "graph_version"],
            ["graph_nodes.id", "graph_nodes.graph_version"],
            name=op.f("fk_vendor_master_supplier_site_id_graph_nodes"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_vendor_master")),
    )
    op.create_table(
        "purchasing_documents",
        sa.Column("id", sa.String(length=96), nullable=False),
        sa.Column("dataset_version", sa.String(length=96), nullable=False),
        sa.Column("vendor_id", sa.String(length=96), nullable=False),
        sa.Column("component_id", sa.String(length=96), nullable=False),
        sa.Column("plant_id", sa.String(length=96), nullable=False),
        sa.Column("graph_version", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=48), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("expected_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('in_transit','received','cancelled')",
            name=op.f("ck_purchasing_documents_status"),
        ),
        sa.CheckConstraint("length(trim(unit)) > 0", name=op.f("ck_purchasing_documents_unit")),
        sa.CheckConstraint(
            "quantity >= 0 AND quantity <= 1.7976931348623157e308",
            name=op.f("ck_purchasing_documents_quantity"),
        ),
        sa.ForeignKeyConstraint(
            ["component_id", "graph_version"],
            ["graph_nodes.id", "graph_nodes.graph_version"],
            name=op.f("fk_purchasing_documents_component_id_graph_nodes"),
        ),
        sa.ForeignKeyConstraint(
            ["dataset_version"],
            ["erp_datasets.id"],
            name=op.f("fk_purchasing_documents_dataset_version_erp_datasets"),
        ),
        sa.ForeignKeyConstraint(
            ["plant_id", "graph_version"],
            ["graph_nodes.id", "graph_nodes.graph_version"],
            name=op.f("fk_purchasing_documents_plant_id_graph_nodes"),
        ),
        sa.ForeignKeyConstraint(
            ["vendor_id"],
            ["vendor_master.id"],
            name=op.f("fk_purchasing_documents_vendor_id_vendor_master"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_purchasing_documents")),
    )


def downgrade() -> None:
    op.drop_table("purchasing_documents")
    op.drop_table("vendor_master")
    op.drop_table("plant_stock")
    op.drop_table("lead_times")
    op.drop_table("bom_items")
    op.drop_table("erp_datasets")
