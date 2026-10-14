"""Portable platform schema; each business key is scoped by tenant."""

from datetime import datetime

from sqlalchemy import JSON, ForeignKey, ForeignKeyConstraint, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from substrata.database import Base as LegacyBase
from substrata.models import UTCDateTime


class Base(DeclarativeBase):
    metadata = LegacyBase.metadata.__class__(
        naming_convention=LegacyBase.metadata.naming_convention
    )


class Organisation(Base):
    __tablename__ = "organisations"
    tenant_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    name: Mapped[str] = mapped_column(String(256))
    version: Mapped[int] = mapped_column(Integer, default=0)
    audit_sequence: Mapped[int] = mapped_column(Integer, default=0)
    audit_head: Mapped[str] = mapped_column(String(64), default="0" * 64)
    policy: Mapped[dict] = mapped_column(JSON, default=dict)


class GraphRevision(Base):
    __tablename__ = "graph_revisions"
    tenant_id: Mapped[str] = mapped_column(ForeignKey("organisations.tenant_id"), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    recorded_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    sha256: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON)


class AuditRecord(Base):
    __tablename__ = "platform_audit"
    tenant_id: Mapped[str] = mapped_column(ForeignKey("organisations.tenant_id"), primary_key=True)
    sequence: Mapped[int] = mapped_column(Integer, primary_key=True)
    previous_hash: Mapped[str] = mapped_column(String(64))
    payload_hash: Mapped[str] = mapped_column(String(64))
    event_type: Mapped[str] = mapped_column(String(96))
    actor: Mapped[str] = mapped_column(String(256))
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime())
    payload: Mapped[dict] = mapped_column(JSON)


class Document(Base):
    __tablename__ = "documents"
    tenant_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    text: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    provenance: Mapped[dict] = mapped_column(JSON)
    __table_args__ = (ForeignKeyConstraint(["tenant_id"], ["organisations.tenant_id"]),)


class WorkRecord(Base):
    __tablename__ = "work_records"
    tenant_id: Mapped[str] = mapped_column(ForeignKey("organisations.tenant_id"), primary_key=True)
    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    kind: Mapped[str] = mapped_column(String(48))
    status: Mapped[str] = mapped_column(String(48))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())
    payload: Mapped[dict] = mapped_column(JSON)
    __table_args__ = (Index("ix_work_records_inbox", "tenant_id", "kind", "status"),)
