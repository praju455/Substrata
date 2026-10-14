"""Tenant feed isolation, transparent heuristic confidence and durable job recovery."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException

from substrata.platform.auth import Principal
from substrata.platform.database import tenant_transaction
from substrata.platform.domain import Provenance
from substrata.platform.events import EventRule, EventSubmission, RSSFeed, ingest, subscription
from substrata.platform.jobs import JobInput, enqueue, jobs, run_next
from substrata.platform.models import WorkRecord
from substrata.platform.records import list_records
from substrata.platform.seeds import generate


def actor(tenant="alpha", role="admin"):
    return Principal(subject="risk-user", tenant_id=tenant, roles={role})


def source(uri="upload://event"):
    now = datetime.now(UTC)
    return Provenance(uri=uri, observed_at=now, kind="uploaded", note="Analyst-submitted event.")


def seeded(platform):
    data = generate("pharma")
    platform.save("alpha", data, "risk-user", expected_version=0)
    return data


def submitted(data, *, id="source-1", title=None, uri="upload://event"):
    now = datetime.now(UTC)
    entity = next(e for e in data.entities if e.id == "upstream")
    return EventSubmission(
        source_id=id,
        title=title or f"Production halt at {entity.name}",
        description="A factory closure is affecting supply.",
        observed_at=now,
        provenance=source(uri),
    )


def test_event_ingestion_deduplicates_maps_with_source_and_creates_tenant_alert(platform):
    data = seeded(platform)
    subscription(
        platform,
        actor(),
        EventRule(categories={"supply_disruption"}, minimum_severity=0.5),
        "supply",
    )
    event = submitted(data)
    first = ingest(platform, "alpha", event)
    duplicate = ingest(platform, "alpha", event)

    assert first["id"] == duplicate["id"]
    assert first["status"] == "matched"
    assert first["payload"]["category"] == "supply_disruption"
    assert first["payload"]["severity"]["provenance"]["kind"] == "assumption"
    assert first["payload"]["matches"][0]["entity_id"] == "upstream"
    assert first["payload"]["matches"][0]["provenance"]["kind"] == "synthetic"
    alerts = list_records(platform, "alpha", kind="alert")
    assert len(alerts) == 1
    assert list_records(platform, "beta", kind="event") == []
    assert list_records(platform, "beta", kind="alert") == []
    assert platform.audit("alpha")["verification"]["valid"]


def test_ambiguous_or_missing_event_match_waits_for_analyst_review(platform):
    data = seeded(platform)
    result = ingest(
        platform,
        "alpha",
        submitted(
            data,
            id="source-ambiguous",
            title="Port congestion slows deliveries in Manila",
            uri="upload://ambiguous",
        ),
    )
    assert result["status"] == "needs_review"


def test_feed_hosts_require_https_and_explicit_allowlist():
    with pytest.raises(ValueError, match="HTTPS"):
        RSSFeed("http://example.com/feed.xml", {"example.com"})
    with pytest.raises(ValueError, match="allowlist"):
        RSSFeed("https://example.com/feed.xml", {"other.example"})
    with pytest.raises(ValueError, match="allowlist"):
        RSSFeed("https://example.com@127.0.0.1/feed.xml", {"example.com"})


def test_job_is_idempotent_durable_and_dispatches_scoped_feed_poll(platform, monkeypatch):
    actor_admin = actor()
    item = JobInput(kind="event_poll", idempotency_key="daily-poll")
    first = enqueue(platform, actor_admin, item)
    assert enqueue(platform, actor_admin, item)["id"] == first["id"]
    assert len(jobs(platform, "alpha")) == 1

    monkeypatch.setattr("substrata.platform.events.poll", lambda store, tenant: [])
    complete = run_next(platform, actor_admin)
    assert complete["status"] == "succeeded"
    assert run_next(platform, actor_admin) is None
    assert jobs(platform, "beta") == []
    assert platform.audit("alpha")["verification"]["valid"]


def test_failed_jobs_preserve_retry_state_and_retry_after_lease(monkeypatch, platform):
    actor_admin = actor()
    job = enqueue(
        platform, actor_admin, JobInput(kind="event_poll", idempotency_key="failing-poll")
    )
    monkeypatch.setattr(
        "substrata.platform.events.poll",
        lambda store, tenant: (_ for _ in ()).throw(TimeoutError()),
    )
    retried = run_next(platform, actor_admin)
    assert retried["status"] == "retry_scheduled"
    with tenant_transaction(platform.engine, "alpha") as session:
        record = session.get(WorkRecord, ("alpha", job["id"]))
        assert record.payload["attempts"] == 1
        assert record.payload["error"] == "TimeoutError"
        record.payload = {
            **record.payload,
            "retry_at": (datetime.now(UTC) - timedelta(seconds=1)).isoformat(),
        }
    monkeypatch.setattr("substrata.platform.events.poll", lambda store, tenant: [])
    assert run_next(platform, actor_admin)["status"] == "succeeded"


def test_job_payload_validation_and_role_checks(platform):
    with pytest.raises(ValueError, match="do not accept"):
        JobInput(kind="event_poll", idempotency_key="poll", payload={"url": "https://example.com"})
    with pytest.raises(ValueError, match="fields are incomplete"):
        JobInput(
            kind="assessment",
            idempotency_key="assessment",
            payload={"graph_version": 1, "assessment": {"source_id": "upstream"}},
        )
    with pytest.raises(ValueError, match="not registered"):
        enqueue(platform, actor(), JobInput.model_construct(kind="arbitrary", idempotency_key="x"))
    with pytest.raises(HTTPException, match="role"):
        enqueue(platform, actor(role="viewer"), JobInput(kind="event_poll", idempotency_key="poll"))
