"""Mapper schema boundaries, deterministic replies and measured fixture evaluation."""

import pytest
from sqlalchemy import func, select

from substrata.agent_models import AgentRun, EvaluationRun
from substrata.database import build_engine, transaction, upgrade_database
from substrata.evaluation import evaluate
from substrata.llm import (
    GeminiClient,
    GrokClient,
    MockLLMClient,
    PrimaryFallbackClient,
    ProviderError,
)
from substrata.mapper import map_evidence, simulate_replies
from substrata.models import GraphEdge
from substrata.seed import seed_database, write_fixtures


@pytest.fixture
def mapped_database(tmp_path):
    write_fixtures(tmp_path)
    engine = build_engine(tmp_path / "mapper.sqlite3")
    upgrade_database(engine)
    seed_database(engine, tmp_path)
    yield engine, tmp_path
    engine.dispose()


def test_mapping_and_simulated_confirmation_without_truth_leak(mapped_database):
    engine, directory = mapped_database
    # The mapper still works when the truth file is unavailable.
    truth = directory / "true_graph.json"
    saved = truth.read_text()
    truth.unlink()
    result = map_evidence(engine)
    assert len(result["inferred"]) == 2
    assert len(result["confirmation_requests"]) == 3
    truth.write_text(saved)
    replies = simulate_replies(engine, truth)
    assert sorted(r["decision"] for r in replies) == ["confirmed", "confirmed", "rejected"]
    assert simulate_replies(engine, truth) == []
    with transaction(engine) as session:
        rejected = session.get(GraphEdge, ("owned_by_site_t2_3_site_shared_source", 1))
        assert rejected.status == "rejected"
        assert rejected.primary_evidence_id == "evidence_4"
    assert len(map_evidence(engine)["inferred"]) == 0


def test_invalid_model_output_writes_no_relationships(mapped_database):
    engine, _ = mapped_database

    class BadClient(MockLLMClient):
        def generate_structured(self, **kwargs):
            return {
                "links": [
                    {
                        "from_id": "site_t2_0",
                        "to_id": "site_shared_source",
                        "evidence_id": "evidence_0",
                        "quote": "Invented quote not in source.",
                        "edge_type": "OWNED_BY",
                    }
                ]
            }

    with pytest.raises(ValueError, match="quote"):
        map_evidence(engine, BadClient())
    with transaction(engine) as session:
        assert session.get(GraphEdge, ("owned_by_site_t2_0_site_shared_source", 1)) is None
        assert (
            session.scalar(
                select(func.count()).select_from(AgentRun).where(AgentRun.status == "failed")
            )
            == 1
        )


def test_measured_evaluation_is_repeatable_and_stored(mapped_database):
    engine, _ = mapped_database
    first = evaluate(engine)
    assert evaluate(engine) == first
    assert first["metrics"]["true_positives"] == 2
    assert first["metrics"]["false_negatives"] == 2
    assert first["metrics"]["precision"] == 1
    assert first["metrics"]["recall"] == 0.5
    assert first["metrics"]["warning_days_gained_vs_tier1"] == 18
    with transaction(engine) as session:
        assert session.scalar(select(func.count()).select_from(EvaluationRun)) == 2


def test_mapper_records_actual_backup_and_attempts(mapped_database, monkeypatch):
    engine, _ = mapped_database
    client = PrimaryFallbackClient(GeminiClient("test"), GrokClient("test"))

    def unavailable(**kwargs):
        raise ProviderError("gemini", "http_429", "Rate limited.")

    monkeypatch.setattr(client.primary, "generate_structured", unavailable)
    monkeypatch.setattr(client.backup, "generate_structured", MockLLMClient().generate_structured)
    result = map_evidence(engine, client)
    assert result["provider"] == "grok"
    assert [a["status"] for a in result["llm_attempts"]] == ["failed", "completed"]
    with transaction(engine) as session:
        run = session.get(AgentRun, result["run_id"])
        assert run.provider == "grok"
        assert run.output["llm_attempts"] == result["llm_attempts"]
