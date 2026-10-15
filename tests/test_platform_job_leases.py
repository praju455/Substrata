"""Expired workers cannot overwrite a later attempt or its durable checkpoints."""

from datetime import UTC, datetime, timedelta

import pytest

from substrata.platform.auth import Principal
from substrata.platform.database import tenant_transaction
from substrata.platform.jobs import JobInput, enqueue, jobs, run_next
from substrata.platform.models import WorkRecord


def expire_lease(store, tenant, job_id):
    with tenant_transaction(store.engine, tenant) as session:
        record = session.get(WorkRecord, (tenant, job_id))
        record.payload = {
            **record.payload,
            "lease_until": (datetime.now(UTC) - timedelta(seconds=1)).isoformat(),
        }


def exercise_reclaimed_job(store, tenant, monkeypatch, late_failure):
    actor = Principal(subject="lease-worker", tenant_id=tenant, roles={"admin"})
    queued = enqueue(store, actor, JobInput(kind="event_poll", idempotency_key="lease-race"))
    calls = []
    successor = []

    def slow_poll(store, tenant):
        calls.append(tenant)
        if len(calls) == 1:
            expire_lease(store, tenant, queued["id"])
            successor.append(run_next(store, actor))
            if late_failure:
                raise TimeoutError("The original request returned after reclamation.")
            return ["old-attempt"]
        return ["new-attempt"]

    monkeypatch.setattr("substrata.platform.events.poll", slow_poll)
    original = run_next(store, actor)
    assert original["status"] == "lease_lost"
    assert successor[0]["status"] == "succeeded"
    persisted = next(record for record in jobs(store, tenant) if record["id"] == queued["id"])
    assert persisted["status"] == "succeeded"
    assert persisted["payload"]["attempts"] == 2
    assert persisted["payload"]["result"] == {"processed": ["new-attempt"]}
    assert "claim_id" not in persisted["payload"]
    audit = store.audit(tenant)
    events = [record["event_type"] for record in audit["records"]]
    assert events.count("job.completed") == 1
    assert "job.retry_scheduled" not in events
    assert audit["verification"]["valid"]


@pytest.mark.parametrize("late_failure", [False, True])
def test_reclaimed_job_keeps_newer_success(platform, monkeypatch, late_failure):
    exercise_reclaimed_job(platform, "alpha", monkeypatch, late_failure)


def test_expired_plan_does_not_publish_checkpoint_or_call_next_tool(platform, monkeypatch):
    from substrata.platform import agent_protocols, governance
    from substrata.platform.records import list_records
    from substrata.platform.seeds import generate

    actor = Principal(subject="lease-worker", tenant_id="alpha", roles={"admin"})
    snapshot = platform.save("alpha", generate("pharma"), actor.subject, expected_version=0)
    queued = enqueue(
        platform,
        actor,
        JobInput(
            kind="agent_plan",
            idempotency_key="expired-plan",
            payload={
                "plan": "risk_review",
                "arguments": {
                    "source_id": "upstream",
                    "severity": 0.8,
                    "as_of": datetime.now(UTC).isoformat(),
                    "graph_version": snapshot.version,
                },
            },
        ),
    )
    original_save = governance.save_assessment
    calls = []

    def delayed_assessment(*args, **kwargs):
        result = original_save(*args, **kwargs)
        expire_lease(platform, "alpha", queued["id"])
        return result

    def forbidden_next_tool(*args, **kwargs):
        calls.append("audit.verify")
        raise AssertionError("An expired plan must not execute another step.")

    monkeypatch.setattr(governance, "save_assessment", delayed_assessment)
    monkeypatch.setattr(agent_protocols, "execute_tool", forbidden_next_tool)
    assert run_next(platform, actor)["status"] == "lease_lost"
    assert calls == []
    assert not jobs(platform, "alpha")[0]["payload"].get("checkpoints")
    # The first tool's idempotent result survives and can be reused by recovery.
    assert len(list_records(platform, "alpha", kind="assessment")) == 1
    monkeypatch.setattr(governance, "save_assessment", original_save)
    monkeypatch.undo()
    assert run_next(platform, actor)["status"] == "succeeded"
    assert len(list_records(platform, "alpha", kind="assessment")) == 1
    assert platform.audit("alpha")["verification"]["valid"]
