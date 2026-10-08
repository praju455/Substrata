"""Recorded agent steps, simulated confirmations and measured evaluations."""

from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from substrata.database import Base
from substrata.models import UTCDateTime


class AgentRun(Base):
    __tablename__ = "agent_runs"
    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    agent: Mapped[str] = mapped_column(String(48))
    status: Mapped[str] = mapped_column(String(24))
    provider: Mapped[str] = mapped_column(String(96))
    model: Mapped[str] = mapped_column(String(96))
    prompt_version: Mapped[str] = mapped_column(String(48))
    latency_ms: Mapped[float] = mapped_column(Float)
    schema_valid: Mapped[bool]
    output: Mapped[dict] = mapped_column(JSON)


class ToolCall(Base):
    __tablename__ = "tool_calls"
    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    agent_run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id"))
    tool: Mapped[str] = mapped_column(String(96))
    summary: Mapped[dict] = mapped_column(JSON)


class ConfirmationRequest(Base):
    __tablename__ = "confirmation_requests"
    __table_args__ = (
        CheckConstraint("status IN ('pending','confirmed','rejected')", name="status"),
    )
    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    edge_id: Mapped[str] = mapped_column(String(96), unique=True)
    graph_version: Mapped[int] = mapped_column(Integer)
    evidence_id: Mapped[str] = mapped_column(ForeignKey("evidence_records.id"))
    confidence: Mapped[float] = mapped_column(Float)
    quote: Mapped[str] = mapped_column(Text)
    candidate: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(24), default="pending", server_default="pending")


class ConfirmationResponse(Base):
    __tablename__ = "confirmation_responses"
    __table_args__ = (CheckConstraint("decision IN ('confirmed','rejected')", name="decision"),)
    request_id: Mapped[str] = mapped_column(
        ForeignKey("confirmation_requests.id"), primary_key=True
    )
    decision: Mapped[str] = mapped_column(String(24))
    responder: Mapped[str] = mapped_column(String(96))
    responded_at: Mapped[datetime] = mapped_column(UTCDateTime())
    rationale: Mapped[str] = mapped_column(Text)


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"
    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    dataset_version: Mapped[str] = mapped_column(String(96))
    seed: Mapped[int] = mapped_column(Integer)
    config: Mapped[dict] = mapped_column(JSON)
    metrics: Mapped[dict] = mapped_column(JSON)


class EvaluationExample(Base):
    __tablename__ = "evaluation_examples"
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    evaluation_run_id: Mapped[str] = mapped_column(ForeignKey("evaluation_runs.id"))
    edge_id: Mapped[str] = mapped_column(String(96))
    expected: Mapped[bool]
    predicted: Mapped[bool]


class EvaluationMetric(Base):
    __tablename__ = "evaluation_metrics"
    evaluation_run_id: Mapped[str] = mapped_column(
        ForeignKey("evaluation_runs.id"), primary_key=True
    )
    name: Mapped[str] = mapped_column(String(96), primary_key=True)
    value: Mapped[float] = mapped_column(Float)
