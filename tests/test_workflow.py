"""Mock-only end-to-end replay, API gates, SSE reset and reproducibility."""

import hashlib
import time

import pytest
from fastapi.testclient import TestClient

from substrata.app import create_app
from substrata.database import build_engine, upgrade_database
from substrata.runtime import Runtime
from substrata.seed import canonical, seed_database, write_fixtures


@pytest.fixture
def runtime(tmp_path):
    write_fixtures(tmp_path)
    engine = build_engine(tmp_path / "workflow.sqlite3")
    upgrade_database(engine)
    seed_database(engine, tmp_path)
    instance = Runtime(engine, tmp_path)
    yield instance
    engine.dispose()


def wait_replay(client):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        state = client.get("/state").json()
        if not state["replay"]["active"]:
            return state
        time.sleep(0.05)
    raise AssertionError("Replay did not finish.")


def test_full_loop_through_api_and_sse(runtime):
    with TestClient(create_app(runtime)) as client:
        assert client.post("/mapper/run").status_code == 200
        replies = client.post("/confirmations/simulate", json={}).json()["replies"]
        assert len(replies) == 3
        assert client.post("/replay/start", json={"event_limit": 1}).status_code == 200
        state = wait_replay(client)
        assert state["scenarios"][0]["report"]["impacts"][0]["cover_days"] == 18
        assert state["scenarios"][0]["report"]["impacts"][0]["exposure_window"] == 72
        action = next(a for a in state["actions"] if a["kind"] == "buffer_buy")
        decision = client.post(
            f"/approvals/{action['id']}/decision",
            json={
                "actor": "Demo approver",
                "role": "procurement_approver",
                "decision": "approved",
                "reason": "Protect the synthetic plan",
            },
        )
        assert decision.status_code == 200
        assert decision.json()["external_execution"] == "simulated_only"
        assert client.get("/audit/verify").json()["valid"]
        assert not client.get("/audit/verify?expected_head=incorrect").json()["valid"]
        stream = client.get("/stream?once=true")
        assert stream.headers["content-type"].startswith("text/event-stream")
        assert '"event_type": "cascade_result"' in stream.text
        assert '"event_type": "approved"' in stream.text
        old_generation = state["generation"]
        assert client.post("/replay/reset").status_code == 200
        reset = client.get("/state").json()
        assert reset["generation"] != old_generation
        assert reset["scenarios"] == []
        assert all(e["status"] == "declared" for e in reset["graph"]["edges"])
        stream = client.get(
            "/stream?once=true", headers={"Last-Event-ID": f"{old_generation}:9999"}
        )
        assert "event: reset" in stream.text
        assert '"event_type": "reset"' in stream.text


def test_stale_approval_requires_new_immutable_run(runtime):
    with TestClient(create_app(runtime)) as client:
        client.post("/mapper/run")
        client.post("/replay/start", json={})
        before = wait_replay(client)
        action = next(a for a in before["actions"] if a["kind"] == "buffer_buy")
        client.post("/confirmations/simulate", json={})  # Changes the graph snapshot.
        response = client.post(
            f"/approvals/{action['id']}/decision",
            json={
                "actor": "Planner",
                "role": "planning_approver",
                "decision": "approved",
                "reason": "Review",
            },
        )
        assert response.status_code == 409
        scenario = before["scenarios"][0]
        assert client.post(f"/scenarios/{scenario['id']}/refresh").status_code == 200
        after = client.get("/state").json()
        assert len(after["scenarios"]) == 2
        assert after["scenarios"][0]["report"] == scenario["report"]


def test_ambiguous_event_escalates_then_named_analyst_resolves(runtime):
    runtime.map()
    for _ in range(4):
        runtime.process_next()
    state = runtime.state()
    event = next(e for e in state["events"] if e["id"] == "event_3")
    assert event["status"] == "NEEDS_REVIEW"
    assert event["candidates"]
    with TestClient(create_app(runtime)) as client:
        result = client.post(
            "/events/event_3/resolve",
            json={
                "node_id": "site_shared_source",
                "actor": "Demo analyst",
                "reason": "Selected the synthetic semiconductor parent",
            },
        )
        assert result.status_code == 200
        assert client.get("/audit/verify").json()["valid"]


def test_ten_seeded_semantic_replays_have_identical_hashes(runtime):
    hashes = []
    for _ in range(10):
        runtime.reset()
        runtime.map()
        runtime.confirm()
        runtime.process_next()
        state = runtime.state()
        action = next(a for a in state["actions"] if a["kind"] == "buffer_buy")
        runtime.decide(
            action["id"],
            {
                "actor": "Fixture approver",
                "role": "planning_approver",
                "decision": "approved",
                "reason": "Repeatability test",
            },
        )
        state = runtime.state()
        semantic = {
            "graph": state["graph"],
            "reports": [s["report"] for s in state["scenarios"]],
            "actions": state["actions"],
        }
        hashes.append(hashlib.sha256(canonical(semantic).encode()).hexdigest())
        assert state["audit"]["valid"]
    assert len(set(hashes)) == 1


def test_cors_and_pause_resume_controls(runtime):
    with TestClient(create_app(runtime)) as client:
        response = client.options(
            "/mapper/run",
            headers={"Origin": "http://127.0.0.1:3000", "Access-Control-Request-Method": "POST"},
        )
        assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"
        assert client.post("/replay/start", json={"event_limit": 6}).status_code == 200
        assert client.post("/replay/pause").json() == {"active": False}
        assert client.post("/replay/start", json={"event_limit": 1}).status_code == 200
        assert wait_replay(client)["replay"]["processed"] >= 1
