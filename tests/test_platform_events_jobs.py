"""Tenant feed isolation, transparent heuristic confidence and durable job recovery."""

import csv
import io
from datetime import UTC, datetime, timedelta
from urllib.error import HTTPError

import pytest
from fastapi import HTTPException

from substrata.platform import agent_protocols
from substrata.platform.auth import Principal
from substrata.platform.database import tenant_transaction
from substrata.platform.domain import Entity, Provenance
from substrata.platform.events import (
    EventRule,
    EventSubmission,
    FeedItem,
    GDELTFeed,
    ITACSLFeed,
    JSONAPIEventFeed,
    MeteoAlarmFeed,
    NWSWeatherFeed,
    OFACSDNFeed,
    RSSFeed,
    ingest,
    poll,
    subscription,
)
from substrata.platform.jobs import MAX_ACTIVE_JOBS_PER_TENANT, JobInput, enqueue, jobs, run_next
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


def test_gdelt_adapter_is_allowlisted_and_bounds_query_window_and_results():
    allowed = {GDELTFeed.HOST}
    feed = GDELTFeed('"port closure" OR "factory shutdown"', allowed, max_records=25)
    parsed = __import__("urllib.parse", fromlist=["urlsplit", "parse_qs"])
    url = parsed.urlsplit(feed.reader.url)
    values = parsed.parse_qs(url.query)
    assert url.hostname == GDELTFeed.HOST
    assert values["mode"] == ["artlist"]
    assert values["format"] == ["rss"]
    assert values["maxrecords"] == ["25"]
    with pytest.raises(ValueError, match="allowlist"):
        GDELTFeed("supplier disruption", set())
    with pytest.raises(ValueError, match="timespan"):
        GDELTFeed("supplier disruption", allowed, timespan="3months")
    with pytest.raises(ValueError, match="max_records"):
        GDELTFeed("supplier disruption", allowed, max_records=250)


def test_gdelt_feed_configuration_runs_through_tenant_event_pipeline(
    platform, monkeypatch, tmp_path
):
    seeded(platform)
    feed_config = tmp_path / "feeds.json"
    feed_config.write_text(
        '[{"type":"gdelt","name":"global-news","tenant_id":"alpha",'
        '"query":"factory closure","license":"GDELT metadata attribution",'
        '"timespan":"24h","max_records":10}]',
        encoding="utf-8",
    )
    monkeypatch.setenv("SUBSTRATA_EVENT_FEEDS_FILE", str(feed_config))
    monkeypatch.setenv("SUBSTRATA_EVENT_ALLOWED_HOSTS", GDELTFeed.HOST)
    monkeypatch.setattr(
        GDELTFeed,
        "read",
        lambda self: [
            FeedItem(
                id="https://news.example/story-1",
                title="Factory closure halts production",
                observed_at=datetime.now(UTC),
            )
        ],
    )
    received = poll(platform, "alpha")
    assert len(received) == 1
    assert received[0]["payload"]["provenance"]["note"].startswith("global-news;")
    assert poll(platform, "beta") == []


def test_nws_weather_adapter_bounds_configuration_and_normalizes_alerts(monkeypatch):
    feed = NWSWeatherFeed("CA", {NWSWeatherFeed.HOST}, "Substrata tests (ops@example.test)")
    assert feed.url == "https://api.weather.gov/alerts/active?area=CA"
    with pytest.raises(ValueError, match="area"):
        NWSWeatherFeed("california", {NWSWeatherFeed.HOST}, "Substrata tests")
    with pytest.raises(ValueError, match="allowlist"):
        NWSWeatherFeed("CA", set(), "Substrata tests")
    with pytest.raises(ValueError, match="User-Agent"):
        NWSWeatherFeed("CA", {NWSWeatherFeed.HOST}, "")

    body = {
        "features": [
            {
                "id": "https://api.weather.gov/alerts/urn:oid:test-1",
                "properties": {
                    "headline": "Flood Warning",
                    "event": "Flood Warning",
                    "description": "Flooding threatens roads.",
                    "areaDesc": "Example County",
                    "severity": "Severe",
                    "sent": "2026-10-14T10:00:00+00:00",
                },
            },
            {
                "id": "https://attacker.example/alerts/2",
                "properties": {"headline": "Untrusted"},
            },
        ]
    }

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def geturl(self):
            return feed.url

        def read(self, limit):
            import json

            return json.dumps(body).encode()

    class Opener:
        def open(self, request, timeout):
            assert request.get_header("User-agent") == "Substrata tests (ops@example.test)"
            assert timeout == 10
            return Response()

    monkeypatch.setattr("urllib.request.build_opener", lambda *handlers: Opener())
    alerts = feed.read()
    assert len(alerts) == 1
    assert alerts[0].id == body["features"][0]["id"]
    assert alerts[0].title == "Flood Warning"
    assert "Example County" in alerts[0].description
    assert "NWS severity: Severe" in alerts[0].description
    assert alerts[0].observed_at == datetime.fromisoformat("2026-10-14T10:00:00+00:00")


def test_nws_weather_feed_uses_tenant_pipeline(platform, monkeypatch, tmp_path):
    seeded(platform)
    feed_config = tmp_path / "feeds.json"
    feed_config.write_text(
        '[{"type":"nws_weather","name":"nws-california","tenant_id":"alpha",'
        '"area":"CA","license":"U.S. government public data attribution"}]',
        encoding="utf-8",
    )
    monkeypatch.setenv("SUBSTRATA_EVENT_FEEDS_FILE", str(feed_config))
    monkeypatch.setenv("SUBSTRATA_EVENT_ALLOWED_HOSTS", NWSWeatherFeed.HOST)
    monkeypatch.setenv("SUBSTRATA_NWS_USER_AGENT", "Substrata tests (ops@example.test)")
    monkeypatch.setattr(
        NWSWeatherFeed,
        "read",
        lambda self: [
            FeedItem(
                id="https://api.weather.gov/alerts/urn:oid:weather-1",
                title="Flood Warning for Example County",
                description="Flash flooding expected.",
                observed_at=datetime.now(UTC),
            )
        ],
    )
    events = poll(platform, "alpha")
    assert len(events) == 1
    assert events[0]["payload"]["category"] == "weather"
    assert events[0]["payload"]["provenance"]["note"].startswith("nws-california;")
    assert poll(platform, "beta") == []


def test_meteoalarm_feed_uses_bounded_official_atom_country_url(monkeypatch):
    feed = MeteoAlarmFeed("ireland", {MeteoAlarmFeed.HOST})
    assert feed.reader.url == ("https://feeds.meteoalarm.org/feeds/meteoalarm-legacy-atom-ireland")
    with pytest.raises(ValueError, match="country"):
        MeteoAlarmFeed("../ireland", {MeteoAlarmFeed.HOST})
    with pytest.raises(ValueError, match="allowlist"):
        MeteoAlarmFeed("ireland", set())
    monkeypatch.setattr(
        feed.reader,
        "read",
        lambda: [
            FeedItem(
                id="https://feeds.meteoalarm.org/warning/42",
                title="Yellow warning for heavy rain",
                observed_at=datetime.now(UTC),
            )
        ],
    )
    warning = feed.read()[0]
    assert warning.title == "MeteoAlarm weather alert: Yellow warning for heavy rain"


def test_meteoalarm_feed_uses_tenant_event_pipeline(platform, monkeypatch, tmp_path):
    seeded(platform)
    feed_config = tmp_path / "feeds.json"
    feed_config.write_text(
        '[{"type":"meteoalarm","name":"meteoalarm-ireland","tenant_id":"alpha",'
        '"country":"ireland","license":"MeteoAlarm CC BY 4.0; attribution reviewed"}]',
        encoding="utf-8",
    )
    monkeypatch.setenv("SUBSTRATA_EVENT_FEEDS_FILE", str(feed_config))
    monkeypatch.setenv("SUBSTRATA_EVENT_ALLOWED_HOSTS", MeteoAlarmFeed.HOST)
    monkeypatch.setattr(
        MeteoAlarmFeed,
        "read",
        lambda self: [
            FeedItem(
                id="https://feeds.meteoalarm.org/warning/42",
                title="MeteoAlarm weather alert: Yellow warning for heavy rain",
                observed_at=datetime.now(UTC),
            )
        ],
    )
    events = poll(platform, "alpha")
    assert len(events) == 1
    assert events[0]["payload"]["category"] == "weather"
    assert events[0]["payload"]["provenance"]["note"].startswith("meteoalarm-ireland;")
    assert poll(platform, "beta") == []


def test_field_mapped_json_api_feed_is_bounded_and_uses_file_credential(monkeypatch, tmp_path):
    credential = tmp_path / "api.secret"
    credential.write_text("private-token\n", encoding="utf-8")
    feed = JSONAPIEventFeed(
        "https://port-api.example.test/v1/alerts",
        {"port-api.example.test"},
        records_path="data.events",
        id_field="id",
        title_field="headline",
        observed_at_field="created_at",
        description_field="details.summary",
        category_hint="port congestion",
        api_key_file=str(credential),
    )
    body = {
        "data": {
            "events": [
                {
                    "id": "port-42",
                    "headline": "Queue length rising",
                    "created_at": "2026-10-14T10:00:00Z",
                    "details": {"summary": "Terminal delays exceed two days."},
                },
                {"id": "bad-time", "headline": "Ignore", "created_at": "not-a-date"},
            ]
        }
    }

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def geturl(self):
            return feed.url

        def read(self, limit):
            import json

            return json.dumps(body).encode()

    class Opener:
        def open(self, request, timeout):
            assert request.get_header("Authorization") == "Bearer private-token"
            return Response()

    monkeypatch.setattr("urllib.request.build_opener", lambda *handlers: Opener())
    items = feed.read()
    assert len(items) == 1
    assert items[0].id == "port-42"
    assert "port congestion" in items[0].description
    with pytest.raises(ValueError, match="allowlist"):
        JSONAPIEventFeed(
            "https://evil.example.test/v1/alerts",
            {"port-api.example.test"},
            records_path="data.events",
            id_field="id",
            title_field="headline",
            observed_at_field="created_at",
        )
    with pytest.raises(ValueError, match="field paths"):
        JSONAPIEventFeed(
            "https://port-api.example.test/v1/alerts",
            {"port-api.example.test"},
            records_path="data..events",
            id_field="id",
            title_field="headline",
            observed_at_field="created_at",
        )


def test_configured_json_api_signal_uses_shared_event_pipeline(platform, monkeypatch, tmp_path):
    seeded(platform)
    feed_config = tmp_path / "feeds.json"
    feed_config.write_text(
        '[{"type":"json_api","name":"port-status","tenant_id":"alpha",'
        '"url":"https://port-api.example.test/v1/alerts","license":"provider license",'
        '"records_path":"data.events","id_field":"id","title_field":"headline",'
        '"observed_at_field":"created_at","description_field":"details",'
        '"category_hint":"port congestion"}]',
        encoding="utf-8",
    )
    monkeypatch.setenv("SUBSTRATA_EVENT_FEEDS_FILE", str(feed_config))
    monkeypatch.setenv("SUBSTRATA_EVENT_ALLOWED_HOSTS", "port-api.example.test")
    monkeypatch.setattr(
        JSONAPIEventFeed,
        "read",
        lambda self: [
            FeedItem(
                id="port-42",
                title="Queue length rising",
                description=(
                    "Terminal delays exceed two days. Operator category hint: port congestion"
                ),
                observed_at=datetime.now(UTC),
            )
        ],
    )
    events = poll(platform, "alpha")
    assert len(events) == 1
    assert events[0]["payload"]["category"] == "transport"
    assert poll(platform, "beta") == []


def test_ofac_sdn_xml_generates_review_only_supplier_name_candidates(
    platform, monkeypatch, tmp_path
):
    data = generate("pharma")
    entities = [
        entity.model_copy(update={"name": "Acme Logistics Inc"})
        if entity.id == "supplier-0"
        else entity.model_copy(update={"name": "Acme Logistics LCC"})
        if entity.id == "supplier-1"
        else entity
        for entity in data.entities
    ]
    platform.save(
        "alpha", data.model_copy(update={"entities": entities}), "risk-user", expected_version=0
    )
    subscription(
        platform, actor(), EventRule(categories={"sanctions"}, minimum_severity=0.5), "sanctions"
    )
    feed_config = tmp_path / "feeds.json"
    feed_config.write_text(
        '[{"type":"ofac_sdn","name":"ofac-sdn","tenant_id":"alpha",'
        '"license":"OFAC public list; operator attribution reviewed"}]',
        encoding="utf-8",
    )
    monkeypatch.setenv("SUBSTRATA_EVENT_FEEDS_FILE", str(feed_config))
    monkeypatch.setenv("SUBSTRATA_EVENT_ALLOWED_HOSTS", OFACSDNFeed.HOST)
    monkeypatch.setenv("SUBSTRATA_OFAC_USER_AGENT", "Substrata tests (ops@example.test)")
    namespace = OFACSDNFeed.NAMESPACE
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<sdnList xmlns="{namespace}">
  <sdnEntry><uid>12345</uid><lastName>Unrelated Target</lastName><sdnType>Entity</sdnType>
    <programList><program>SDGT</program></programList>
    <akaList><aka><type>a.k.a.</type><category>strong</category>
      <lastName>Acme Logistics Inc</lastName></aka></akaList>
  </sdnEntry>
  <sdnEntry><uid>23456</uid><lastName>Acme Logistics LLC</lastName>
    <sdnType>Entity</sdnType></sdnEntry>
  <sdnEntry><uid>67890</uid><lastName>Other Organization</lastName>
    <sdnType>Entity</sdnType></sdnEntry>
</sdnList>""".encode()

    class Response:
        headers = {"Last-Modified": "Wed, 14 Oct 2026 14:02:23 GMT"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def geturl(self):
            return OFACSDNFeed.URL

        def read(self, limit):
            assert limit == 40_000_001
            return xml

    class Opener:
        def open(self, request, timeout):
            assert request.full_url == OFACSDNFeed.URL
            assert request.get_header("User-agent") == "Substrata tests (ops@example.test)"
            assert timeout == 30
            return Response()

    monkeypatch.setattr("urllib.request.build_opener", lambda *handlers: Opener())
    events = poll(platform, "alpha")
    assert len(events) == 2
    assert all(event["status"] == "needs_review" for event in events)
    assert all(event["payload"]["category"] == "sanctions" for event in events)
    assert all("not a legal determination" in event["payload"]["description"] for event in events)
    assert {event["payload"]["matches"][0]["entity_id"] for event in events} == {
        "supplier-0",
        "supplier-1",
    }
    assert any("heuristic_name_similarity" in event["payload"]["description"] for event in events)
    alerts = list_records(platform, "alpha", kind="alert")
    assert len(alerts) == 2
    assert {event["id"] for event in poll(platform, "alpha")} == {event["id"] for event in events}
    assert list_records(platform, "beta", kind="event") == []
    assert platform.audit("alpha")["verification"]["valid"]


def test_ofac_sdn_reader_requires_allowlist_and_rejects_unbounded_configuration():
    with pytest.raises(ValueError, match="allowlist"):
        OFACSDNFeed(set(), "Substrata tests (ops@example.test)")
    with pytest.raises(ValueError, match="User-Agent"):
        OFACSDNFeed({OFACSDNFeed.HOST}, "")


def test_ofac_sdn_reader_follows_only_the_official_signed_s3_download(monkeypatch):
    entity = Entity(
        id="supplier-acme",
        kind="Supplier",
        name="Acme Holdings LLC",
        provenance=source(),
    )
    feed = OFACSDNFeed({OFACSDNFeed.HOST}, "Substrata tests (ops@example.test)")
    xml = (
        f'<sdnList xmlns="{feed.NAMESPACE}"><sdnEntry><uid>42</uid>'
        "<lastName>Acme Holdings LLC</lastName><sdnType>Entity</sdnType>"
        "</sdnEntry></sdnList>"
    ).encode()
    target = "https://published.s3.us-gov-west-1.amazonaws.com/sdn.xml?signature=secret"

    class Response:
        headers = {"Last-Modified": "Wed, 14 Oct 2026 14:02:23 GMT"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def geturl(self):
            return target

        def read(self, limit):
            return xml

    class Opener:
        calls = 0

        def open(self, request, timeout):
            self.calls += 1
            assert timeout == 30
            if self.calls == 1:
                assert request.full_url == feed.URL
                raise HTTPError(feed.URL, 302, "Found", {"Location": target}, None)
            assert request.full_url == target
            return Response()

    opener = Opener()
    monkeypatch.setattr("urllib.request.build_opener", lambda *handlers: opener)
    assert len(feed.screen([entity])) == 1
    assert opener.calls == 2

    class UntrustedOpener:
        def open(self, request, timeout):
            raise HTTPError(
                feed.URL,
                302,
                "Found",
                {"Location": "https://untrusted.example.test/sdn.xml"},
                None,
            )

    monkeypatch.setattr("urllib.request.build_opener", lambda *handlers: UntrustedOpener())
    with pytest.raises(ValueError, match="untrusted download redirect"):
        feed.screen([entity])


def test_ita_csl_reader_matches_primary_and_alias_names_with_bounded_csv(monkeypatch):
    entities = [
        Entity(
            id="supplier-acme",
            kind="Supplier",
            name="Acme Components Incorporated",
            provenance=source(),
        ),
        Entity(
            id="supplier-alpha",
            kind="Supplier",
            name="Alpha Parts Corporation",
            provenance=source(),
        ),
    ]
    feed = ITACSLFeed({ITACSLFeed.HOST})
    with pytest.raises(ValueError, match="allowlist"):
        ITACSLFeed(set())
    output = io.StringIO(newline="")
    fields = ["_id", "source", "name", "alt_names", "programs", "source_information_url"]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerow(
        {
            "_id": "csl-1",
            "source": "Entity List - BIS",
            "name": "Unrelated Overseas Company",
            "alt_names": "Acme Components Incorporated;Acme C",
            "programs": "EAR99",
            "source_information_url": "https://www.bis.gov/entity-list",
        }
    )
    writer.writerow(
        {
            "_id": "csl-2",
            "source": "Denied Persons List - BIS",
            "name": "Alpha Part Corporation",
            "alt_names": "",
            "programs": "",
            "source_information_url": "https://www.bis.gov/denied-persons-list",
        }
    )
    body = output.getvalue().encode()

    class Response:
        headers = {"Last-Modified": "Wed, 14 Oct 2026 14:02:23 GMT"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def geturl(self):
            return feed.URL

        def read(self, limit):
            assert limit == 30_000_001
            return body

    class Opener:
        def open(self, request, timeout):
            assert request.full_url == feed.URL
            assert request.get_header("Accept") == "text/csv"
            assert timeout == 30
            return Response()

    monkeypatch.setattr("urllib.request.build_opener", lambda *handlers: Opener())
    matches = feed.screen(entities)
    assert {match["entity"].id for match in matches} == {"supplier-acme", "supplier-alpha"}
    assert {match["method"] for match in matches} == {"exact", "heuristic_name_similarity"}
    assert next(match for match in matches if match["uid"] == "csl-1")["source"].startswith(
        "Entity List"
    )


def test_ita_csl_feed_creates_review_only_tenant_candidate(platform, monkeypatch, tmp_path):
    data = generate("pharma")
    platform.save("alpha", data, "risk-user", expected_version=0)
    subscription(
        platform, actor(), EventRule(categories={"sanctions"}, minimum_severity=0.5), "csl"
    )
    entity = next(entity for entity in data.entities if entity.id == "supplier-0")
    observed = datetime.now(UTC)
    feed_config = tmp_path / "feeds.json"
    feed_config.write_text(
        '[{"type":"ita_csl","name":"ita-csl","tenant_id":"alpha",'
        '"license":"ITA terms; required notice displayed"}]',
        encoding="utf-8",
    )
    monkeypatch.setenv("SUBSTRATA_EVENT_FEEDS_FILE", str(feed_config))
    monkeypatch.setenv("SUBSTRATA_EVENT_ALLOWED_HOSTS", ITACSLFeed.HOST)
    monkeypatch.setattr(
        ITACSLFeed,
        "screen",
        lambda self, entities: [
            {
                "entity": entity,
                "uid": "csl-123",
                "listed_name": "Listed Supplier Ltd",
                "aliases": [entity.name],
                "source": "Entity List - BIS",
                "programs": "EAR99",
                "source_url": "https://www.bis.gov/entity-list",
                "score": 1.0,
                "method": "exact",
                "observed_at": observed,
            }
        ],
    )
    events = poll(platform, "alpha")
    assert len(events) == 1
    event = events[0]["payload"]
    assert events[0]["status"] == "needs_review"
    assert event["category"] == "sanctions"
    assert (
        "not endorsed or certified by the International Trade Administration"
        in event["description"]
    )
    assert "not a legal determination" in event["description"]
    assert len(list_records(platform, "alpha", kind="alert")) == 1
    assert list_records(platform, "beta", kind="event") == []


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


def test_specialized_agent_task_runs_typed_deterministic_work_durably(platform):
    seeded(platform)
    snapshot = platform.snapshot("alpha")
    item = JobInput(
        kind="agent_task",
        idempotency_key="cascade-agent-1",
        payload={
            "agent": "cascade_caller",
            "arguments": {
                "source_id": "upstream",
                "severity": 0.8,
                "as_of": datetime.now(UTC).isoformat(),
                "max_depth": 4,
                "graph_version": snapshot.version,
            },
        },
    )
    created = enqueue(platform, actor(), item)
    assert created["payload"]["job_type"] == "agent_task"
    assert enqueue(platform, actor(), item)["id"] == created["id"]
    completed = run_next(platform, actor())
    assert completed["status"] == "succeeded"
    assert completed["payload"]["result"]["graph_version"] == snapshot.version
    assert completed["payload"]["result"]["source_id"] == "upstream"
    assert platform.audit("alpha")["verification"]["valid"]


def test_risk_review_plan_resumes_from_durable_role_checkpoint(platform, monkeypatch):
    seeded(platform)
    snapshot = platform.snapshot("alpha")
    item = JobInput(
        kind="agent_plan",
        idempotency_key="risk-review-plan-1",
        payload={
            "plan": "risk_review",
            "arguments": {
                "source_id": "upstream",
                "severity": 0.8,
                "as_of": datetime.now(UTC).isoformat(),
                "max_depth": 4,
                "graph_version": snapshot.version,
            },
        },
    )
    queued = enqueue(platform, actor(), item)
    original_execute = agent_protocols.execute_tool
    fail_audit = True
    calls = []

    def flaky_execute(store, caller, name, arguments, **kwargs):
        nonlocal fail_audit
        calls.append(name)
        if name == "audit.verify" and fail_audit:
            fail_audit = False
            raise TimeoutError("temporary audit provider failure")
        return original_execute(store, caller, name, arguments, **kwargs)

    monkeypatch.setattr(agent_protocols, "execute_tool", flaky_execute)
    assert run_next(platform, actor())["status"] == "retry_scheduled"
    with tenant_transaction(platform.engine, "alpha") as session:
        record = session.get(WorkRecord, ("alpha", queued["id"]))
        assert set(record.payload.get("checkpoints", {})) == {"cascade_caller.assessment"}, (
            record.payload.get("error")
        )
        record.payload = {
            **record.payload,
            "retry_at": (datetime.now(UTC) - timedelta(seconds=1)).isoformat(),
        }

    completed = run_next(platform, actor())
    assert completed["status"] == "succeeded"
    checkpoints = completed["payload"]["checkpoints"]
    assert set(checkpoints) == {
        "cascade_caller.assessment",
        "compliance_audit.verification",
    }
    assert checkpoints["compliance_audit.verification"]["valid"] is True
    assert calls == ["audit.verify", "audit.verify"]
    assert platform.audit("alpha")["verification"]["valid"]


def test_tenant_job_queue_enforces_active_work_limit(platform):
    for index in range(MAX_ACTIVE_JOBS_PER_TENANT):
        enqueue(
            platform,
            actor(),
            JobInput(kind="event_poll", idempotency_key=f"queued-{index}"),
        )
    with pytest.raises(ValueError, match="active job limit"):
        enqueue(platform, actor(), JobInput(kind="event_poll", idempotency_key="overflow"))
    assert len(jobs(platform, "alpha", limit=MAX_ACTIVE_JOBS_PER_TENANT)) == (
        MAX_ACTIVE_JOBS_PER_TENANT
    )
    assert jobs(platform, "beta") == []


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
    with pytest.raises(ValueError, match="Agent task name"):
        JobInput(
            kind="agent_task",
            idempotency_key="unknown-agent",
            payload={"agent": "unregistered", "arguments": {}},
        )
    with pytest.raises(HTTPException, match="role"):
        enqueue(platform, actor(role="viewer"), JobInput(kind="event_poll", idempotency_key="poll"))
