"""Authoritative graph and provenance records, not graph projection algorithms."""

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from substrata.database import Base
from substrata.graph_types import NODE_ATTRIBUTES, NodeAttributes


class UTCDateTime(TypeDecorator[datetime]):
    """Require timezone-aware input and round-trip SQLite timestamps as UTC."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Timestamp must be timezone-aware.")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        return value.replace(tzinfo=UTC) if value is not None else None


class NodeAttributesJSON(TypeDecorator[NodeAttributes]):
    """Validate required fields for each node type on ORM/Core writes and reads."""

    impl = JSON
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return NODE_ATTRIBUTES.validate_python(value).model_dump(mode="json")

    def process_result_value(self, value, dialect):
        return NODE_ATTRIBUTES.validate_python(value)


class GraphNode(Base):
    __tablename__ = "graph_nodes"
    __table_args__ = (
        UniqueConstraint("id", "graph_version", "node_type"),
        CheckConstraint("graph_version >= 1", name="positive_version"),
        CheckConstraint("length(trim(id)) > 0 AND length(trim(name)) > 0", name="nonempty_labels"),
        CheckConstraint("length(trim(normalized_name)) > 0", name="normalized_name"),
        CheckConstraint("synthetic = 1", name="synthetic_only"),
        CheckConstraint(
            "node_type IN ('Product','Component','SupplierSite','Plant','Region',"
            "'Event','AlternativeSupplier')",
            name="node_type",
        ),
        CheckConstraint(
            "json_type(attributes) = 'object' AND "
            "json_extract(attributes, '$.node_type') IS node_type",
            name="attribute_type",
        ),
        Index("ix_graph_nodes_type_name", "node_type", "normalized_name"),
    )

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    graph_version: Mapped[int] = mapped_column(Integer, primary_key=True)
    node_type: Mapped[str] = mapped_column(String(24))
    name: Mapped[str] = mapped_column(String(256))
    normalized_name: Mapped[str] = mapped_column(String(256))
    attributes: Mapped[NodeAttributes] = mapped_column(NodeAttributesJSON())
    synthetic: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")


class SourceSnapshot(Base):
    __tablename__ = "source_snapshots"
    __table_args__ = (
        CheckConstraint("length(trim(id)) > 0", name="nonempty_id"),
        CheckConstraint("source_kind IN ('synthetic','public_context')", name="source_kind"),
        CheckConstraint(
            "length(content_sha256) = 64 AND content_sha256 NOT GLOB '*[^0-9a-f]*'",
            name="sha256",
        ),
        CheckConstraint(
            "length(trim(source_uri)) > 0 AND length(trim(license_note)) > 0 "
            "AND length(trim(permitted_excerpt)) > 0",
            name="source_provenance",
        ),
    )

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    source_uri: Mapped[str] = mapped_column(Text)
    source_kind: Mapped[str] = mapped_column(String(24))
    observed_at: Mapped[datetime] = mapped_column(UTCDateTime())
    content_sha256: Mapped[str] = mapped_column(String(64))
    permitted_excerpt: Mapped[str] = mapped_column(Text)
    license_note: Mapped[str] = mapped_column(Text)


class EvidenceRecord(Base):
    __tablename__ = "evidence_records"
    __table_args__ = (
        CheckConstraint("length(trim(id)) > 0", name="nonempty_id"),
        CheckConstraint("length(trim(claim)) > 0", name="nonempty_claim"),
        CheckConstraint("reliability >= 0 AND reliability <= 1", name="reliability_range"),
        CheckConstraint("recency_days >= 0", name="recency_nonnegative"),
        Index("ix_evidence_records_snapshot", "source_snapshot_id"),
    )

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    source_snapshot_id: Mapped[str] = mapped_column(ForeignKey("source_snapshots.id"))
    claim: Mapped[str] = mapped_column(Text)
    reliability: Mapped[float | None] = mapped_column(Float)
    recency_days: Mapped[int | None] = mapped_column(Integer)


class GraphEdge(Base):
    __tablename__ = "graph_edges"
    __table_args__ = (
        CheckConstraint("length(trim(id)) > 0", name="nonempty_id"),
        ForeignKeyConstraint(
            ["from_node_id", "graph_version", "from_node_type"],
            ["graph_nodes.id", "graph_nodes.graph_version", "graph_nodes.node_type"],
        ),
        ForeignKeyConstraint(
            ["to_node_id", "graph_version", "to_node_type"],
            ["graph_nodes.id", "graph_nodes.graph_version", "graph_nodes.node_type"],
        ),
        UniqueConstraint("from_node_id", "to_node_id", "edge_type", "valid_from", "graph_version"),
        CheckConstraint("graph_version >= 1", name="positive_version"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_range"),
        CheckConstraint("from_node_id <> to_node_id", name="distinct_endpoints"),
        CheckConstraint(
            "status IN ('declared','inferred','confirmed','rejected','expired')", name="status"
        ),
        CheckConstraint(
            "(edge_type = 'SUPPLIES' AND from_node_type = 'SupplierSite' "
            "AND to_node_type = 'Component') OR "
            "(edge_type = 'USED_IN' AND from_node_type = 'Component' "
            "AND to_node_type IN ('Product','Plant')) OR "
            "(edge_type = 'LOCATED_IN' AND from_node_type IN "
            "('SupplierSite','Plant','Region') AND to_node_type = 'Region') OR "
            "(edge_type = 'OWNED_BY' AND from_node_type = 'SupplierSite' "
            "AND to_node_type = 'SupplierSite')",
            name="typed_direction",
        ),
        CheckConstraint(
            "edge_type <> 'SUPPLIES' OR (share IS NOT NULL AND lead_time_days IS NOT NULL)",
            name="supply_fields",
        ),
        CheckConstraint("share >= 0 AND share <= 1", name="share_range"),
        CheckConstraint("lead_time_days >= 0", name="lead_time_nonnegative"),
        CheckConstraint("bom_quantity > 0", name="bom_quantity_positive"),
        CheckConstraint(
            "lead_time_days <= 1.7976931348623157e308 AND bom_quantity <= 1.7976931348623157e308",
            name="finite_quantities",
        ),
        CheckConstraint(
            "edge_type = 'SUPPLIES' OR (share IS NULL AND lead_time_days IS NULL)",
            name="supply_field_scope",
        ),
        CheckConstraint(
            "edge_type = 'USED_IN' OR (bom_quantity IS NULL AND unit IS NULL)",
            name="bom_field_scope",
        ),
        CheckConstraint(
            "edge_type <> 'USED_IN' OR (bom_quantity IS NOT NULL AND bom_quantity > 0 "
            "AND unit IS NOT NULL AND length(trim(unit)) > 0)",
            name="bom_fields",
        ),
        CheckConstraint(
            "status <> 'inferred' OR primary_evidence_id IS NOT NULL", name="inferred_evidence"
        ),
        CheckConstraint(
            "status <> 'confirmed' OR last_verified IS NOT NULL", name="confirmed_time"
        ),
        CheckConstraint("valid_to IS NULL OR valid_to > valid_from", name="validity_order"),
        Index("ix_graph_edges_path", "from_node_id", "to_node_id", "edge_type", "valid_from"),
        Index("ix_graph_edges_review", "status", "last_verified"),
    )

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    graph_version: Mapped[int] = mapped_column(Integer, primary_key=True)
    from_node_id: Mapped[str] = mapped_column(String(96))
    to_node_id: Mapped[str] = mapped_column(String(96))
    from_node_type: Mapped[str] = mapped_column(String(24))
    to_node_type: Mapped[str] = mapped_column(String(24))
    edge_type: Mapped[str] = mapped_column(String(24))
    confidence: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(16))
    primary_evidence_id: Mapped[str | None] = mapped_column(ForeignKey("evidence_records.id"))
    last_verified: Mapped[datetime | None] = mapped_column(UTCDateTime())
    valid_from: Mapped[datetime] = mapped_column(UTCDateTime())
    valid_to: Mapped[datetime | None] = mapped_column(UTCDateTime())
    share: Mapped[float | None] = mapped_column(Float)
    lead_time_days: Mapped[float | None] = mapped_column(Float)
    bom_quantity: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(48))


class EdgeEvidence(Base):
    __tablename__ = "edge_evidence"
    __table_args__ = (
        ForeignKeyConstraint(
            ["edge_id", "graph_version"], ["graph_edges.id", "graph_edges.graph_version"]
        ),
        CheckConstraint("stance IN ('supports','contradicts')", name="stance"),
    )

    edge_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    graph_version: Mapped[int] = mapped_column(Integer, primary_key=True)
    evidence_id: Mapped[str] = mapped_column(ForeignKey("evidence_records.id"), primary_key=True)
    stance: Mapped[str] = mapped_column(String(16), default="supports", server_default="supports")
