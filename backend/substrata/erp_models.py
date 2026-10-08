"""Synthetic ERP records pinned to a dataset, graph and inventory snapshot."""

from datetime import datetime

from sqlalchemy import CheckConstraint, Float, ForeignKey, ForeignKeyConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from substrata.database import Base
from substrata.models import UTCDateTime


class Dataset(Base):
    __tablename__ = "erp_datasets"
    __table_args__ = (
        CheckConstraint("graph_version >= 1", name="graph_version"),
        CheckConstraint("source_kind = 'synthetic'", name="synthetic_only"),
    )

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    graph_version: Mapped[int] = mapped_column(Integer)
    inventory_snapshot_id: Mapped[str] = mapped_column(String(96), unique=True)
    as_of: Mapped[datetime] = mapped_column(UTCDateTime())
    source_kind: Mapped[str] = mapped_column(
        String(24), default="synthetic", server_default="synthetic"
    )


class VendorMaster(Base):
    __tablename__ = "vendor_master"
    __table_args__ = (
        ForeignKeyConstraint(
            ["supplier_site_id", "graph_version"], ["graph_nodes.id", "graph_nodes.graph_version"]
        ),
    )

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    dataset_version: Mapped[str] = mapped_column(ForeignKey("erp_datasets.id"))
    supplier_site_id: Mapped[str] = mapped_column(String(96))
    graph_version: Mapped[int] = mapped_column(Integer)
    vendor_name: Mapped[str] = mapped_column(String(256))


class PurchasingDocument(Base):
    __tablename__ = "purchasing_documents"
    __table_args__ = (
        CheckConstraint("quantity >= 0 AND quantity <= 1.7976931348623157e308", name="quantity"),
        CheckConstraint("length(trim(unit)) > 0", name="unit"),
        CheckConstraint("status IN ('in_transit','received','cancelled')", name="status"),
        ForeignKeyConstraint(
            ["component_id", "graph_version"], ["graph_nodes.id", "graph_nodes.graph_version"]
        ),
        ForeignKeyConstraint(
            ["plant_id", "graph_version"], ["graph_nodes.id", "graph_nodes.graph_version"]
        ),
    )

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    dataset_version: Mapped[str] = mapped_column(ForeignKey("erp_datasets.id"))
    vendor_id: Mapped[str] = mapped_column(ForeignKey("vendor_master.id"))
    component_id: Mapped[str] = mapped_column(String(96))
    plant_id: Mapped[str] = mapped_column(String(96))
    graph_version: Mapped[int] = mapped_column(Integer)
    quantity: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(48))
    status: Mapped[str] = mapped_column(String(24))
    expected_at: Mapped[datetime] = mapped_column(UTCDateTime())


class BomItem(Base):
    __tablename__ = "bom_items"
    __table_args__ = (
        CheckConstraint("quantity > 0 AND quantity <= 1.7976931348623157e308", name="quantity"),
        CheckConstraint("length(trim(unit)) > 0", name="unit"),
        ForeignKeyConstraint(
            ["component_id", "graph_version"], ["graph_nodes.id", "graph_nodes.graph_version"]
        ),
        ForeignKeyConstraint(
            ["product_id", "graph_version"], ["graph_nodes.id", "graph_nodes.graph_version"]
        ),
    )

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    dataset_version: Mapped[str] = mapped_column(ForeignKey("erp_datasets.id"))
    component_id: Mapped[str] = mapped_column(String(96))
    product_id: Mapped[str] = mapped_column(String(96))
    graph_version: Mapped[int] = mapped_column(Integer)
    quantity: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(48))


class PlantStock(Base):
    __tablename__ = "plant_stock"
    __table_args__ = (
        CheckConstraint("on_hand >= 0 AND on_hand <= 1.7976931348623157e308", name="on_hand"),
        CheckConstraint(
            "daily_consumption >= 0 AND daily_consumption <= 1.7976931348623157e308",
            name="daily_consumption",
        ),
        CheckConstraint("length(trim(unit)) > 0", name="unit"),
        ForeignKeyConstraint(
            ["component_id", "graph_version"], ["graph_nodes.id", "graph_nodes.graph_version"]
        ),
        ForeignKeyConstraint(
            ["plant_id", "graph_version"], ["graph_nodes.id", "graph_nodes.graph_version"]
        ),
    )

    dataset_version: Mapped[str] = mapped_column(ForeignKey("erp_datasets.id"), primary_key=True)
    component_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    plant_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    graph_version: Mapped[int] = mapped_column(Integer)
    inventory_snapshot_id: Mapped[str] = mapped_column(String(96))
    as_of: Mapped[datetime] = mapped_column(UTCDateTime())
    on_hand: Mapped[float | None] = mapped_column(Float)
    daily_consumption: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(48))


class LeadTime(Base):
    __tablename__ = "lead_times"
    __table_args__ = (
        CheckConstraint(
            "requalification_days >= 0 AND requalification_days <= 1.7976931348623157e308",
            name="requalification",
        ),
        CheckConstraint("length(trim(provenance)) > 0", name="provenance"),
        ForeignKeyConstraint(
            ["component_id", "graph_version"], ["graph_nodes.id", "graph_nodes.graph_version"]
        ),
    )

    dataset_version: Mapped[str] = mapped_column(ForeignKey("erp_datasets.id"), primary_key=True)
    component_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    graph_version: Mapped[int] = mapped_column(Integer)
    requalification_days: Mapped[float | None] = mapped_column(Float)
    provenance: Mapped[str] = mapped_column(String(256))
