"""Replay, frozen analysis, simulated proposals, named decisions and audit chain."""

from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from substrata.database import Base
from substrata.models import UTCDateTime


class EventRecord(Base):
    __tablename__ = "events"
    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(48))
    observed_at: Mapped[datetime] = mapped_column(UTCDateTime())
    ingested_at: Mapped[datetime] = mapped_column(UTCDateTime())
    status: Mapped[str] = mapped_column(String(48))
    payload: Mapped[dict] = mapped_column(JSON)


class EventEntityMatch(Base):
    __tablename__ = "event_entity_matches"
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), primary_key=True)
    node_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    score: Mapped[float] = mapped_column(Float)
    method: Mapped[str] = mapped_column(String(48))


class Scenario(Base):
    __tablename__ = "scenarios"
    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"))
    status: Mapped[str] = mapped_column(String(48))
    snapshot: Mapped[dict] = mapped_column(JSON)


class ImpactResult(Base):
    __tablename__ = "impact_results"
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenarios.id"), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)


class ActionProposal(Base):
    __tablename__ = "action_proposals"
    __table_args__ = (CheckConstraint("cost >= 0 AND cost <= 1.7976931348623157e308", name="cost"),)
    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenarios.id"))
    kind: Mapped[str] = mapped_column(String(48))
    title: Mapped[str] = mapped_column(String(256))
    cost: Mapped[float] = mapped_column(Float)
    duration_days: Mapped[float] = mapped_column(Float)
    risk: Mapped[float] = mapped_column(Float)
    rank_score: Mapped[float] = mapped_column(Float)
    policy: Mapped[str] = mapped_column(String(24))
    status: Mapped[str] = mapped_column(String(48))
    rationale: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSON)


class ApprovalRequest(Base):
    __tablename__ = "approval_queue"
    action_id: Mapped[str] = mapped_column(ForeignKey("action_proposals.id"), primary_key=True)
    snapshot_sha256: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime())
    status: Mapped[str] = mapped_column(String(24))


class ApprovalDecision(Base):
    __tablename__ = "approval_decisions"
    action_id: Mapped[str] = mapped_column(ForeignKey("approval_queue.action_id"), primary_key=True)
    actor: Mapped[str] = mapped_column(String(96))
    role: Mapped[str] = mapped_column(String(48))
    decision: Mapped[str] = mapped_column(String(24))
    reason: Mapped[str] = mapped_column(Text)
    decided_at: Mapped[datetime] = mapped_column(UTCDateTime())


class AuditEvent(Base):
    __tablename__ = "audit_events"
    sequence: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    previous_hash: Mapped[str] = mapped_column(String(64))
    payload_hash: Mapped[str] = mapped_column(String(64))
    event_type: Mapped[str] = mapped_column(String(48))
    actor: Mapped[str] = mapped_column(String(96))
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime())
    payload: Mapped[dict] = mapped_column(JSON)


class StreamEvent(Base):
    __tablename__ = "stream_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(48))
    payload: Mapped[dict] = mapped_column(JSON)
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime())


class DemoState(Base):
    __tablename__ = "demo_state"
    id: Mapped[str] = mapped_column(String(24), primary_key=True)
    generation: Mapped[str] = mapped_column(String(48))
