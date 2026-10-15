"""A second manual feed check must observe intraday updates after an earlier job ends."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient
from test_platform_api import KEY, headers

from substrata.app import create_app
from substrata.platform.auth import TokenVerifier
from substrata.platform.domain import Provenance
from substrata.platform.events import EventSubmission, ingest
from substrata.platform.records import list_records


def test_repeat_event_poll_creates_new_work_and_deduplicates_previous_items(platform, monkeypatch):
    now = datetime.now(UTC)
    source = Provenance(
        kind="synthetic",
        uri="synthetic://intraday-feed",
        observed_at=now,
        note="Invented feed items for local regression testing.",
    )
    calls = []

    def changing_feed(store, tenant):
        calls.append(tenant)
        return [
            ingest(
                store,
                tenant,
                EventSubmission(
                    source_id=f"item-{index}",
                    title=f"Synthetic factory closure {index}",
                    description="Invented intraday update.",
                    observed_at=now,
                    provenance=source,
                ),
            )
            for index in range(len(calls))
        ]

    monkeypatch.setattr("substrata.platform.events.poll", changing_feed)
    app = create_app(
        platform_store=platform,
        auth_verifier=TokenVerifier(
            issuer="test-issuer", audience="substrata", key=KEY, algorithm="HS256"
        ),
    )
    with TestClient(app) as client:
        first = client.post("/platform/events/poll", json={}, headers=headers())
        assert first.status_code == 200
        assert (
            client.post("/platform/jobs/dispatch", json={}, headers=headers()).json()["status"]
            == "succeeded"
        )
        second = client.post("/platform/events/poll", json={}, headers=headers())
        assert second.status_code == 200
        assert second.json()["id"] != first.json()["id"]
        assert (
            client.post("/platform/jobs/dispatch", json={}, headers=headers()).json()["status"]
            == "succeeded"
        )
    assert calls == ["alpha", "alpha"]
    assert len(list_records(platform, "alpha", kind="event")) == 2
    assert len(list_records(platform, "alpha", kind="job")) == 2
    assert list_records(platform, "beta", kind="event") == []
    assert platform.audit("alpha")["verification"]["valid"]
