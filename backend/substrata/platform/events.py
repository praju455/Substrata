"""Tenant event feeds, rules, entity matching, deduplication and alert records."""

import hashlib
import html
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from difflib import SequenceMatcher
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Literal, Protocol

from pydantic import AwareDatetime, Field

from substrata.platform.database import tenant_transaction
from substrata.platform.domain import Contract, Identifier, Label, Provenance
from substrata.platform.models import WorkRecord
from substrata.platform.records import add, encode

MAX_FEED_BYTES = 1_000_000
MAX_FEED_ITEMS = 200


class EventSubmission(Contract):
    source_id: Identifier
    title: Label
    description: str = Field(default="", max_length=10000)
    observed_at: AwareDatetime
    provenance: Provenance


class EventRule(Contract):
    categories: set[Literal["supply_disruption", "weather", "transport", "sanctions", "other"]]
    minimum_severity: float = Field(default=0.0, ge=0, le=1, allow_inf_nan=False)
    enabled: bool = True


class FeedItem(Contract):
    id: str = Field(min_length=1, max_length=2048)
    title: Label
    description: str = Field(default="", max_length=10000)
    observed_at: AwareDatetime


class EventFeed(Protocol):
    def read(self) -> list[FeedItem]: ...


class RSSFeed:
    """Bounded RSS/Atom reader; HTTPS and an explicit host allowlist prevent SSRF."""

    def __init__(self, url: str, allowed_hosts: set[str], *, timeout: float = 10):
        parsed = urllib.parse.urlsplit(url)
        host = (parsed.hostname or "").casefold().rstrip(".")
        if (
            parsed.scheme != "https"
            or not host
            or parsed.username
            or parsed.password
            or host not in {item.casefold().rstrip(".") for item in allowed_hosts}
        ):
            raise ValueError("Event feed must use HTTPS on a configured host allowlist.")
        if not 0 < timeout <= 30:
            raise ValueError("Feed timeout must be between 0 and 30 seconds.")
        self.url, self.host, self.timeout = url, host, timeout

    def read(self) -> list[FeedItem]:
        request = urllib.request.Request(
            self.url,
            headers={"Accept": "application/rss+xml, application/atom+xml, application/xml"},
        )
        try:

            class NoRedirect(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, req, fp, code, msg, headers, newurl):
                    return None

            opener = urllib.request.build_opener(NoRedirect)
            with opener.open(request, timeout=self.timeout) as response:
                if response.geturl() != self.url:
                    raise ValueError("Event feed redirects are not allowed.")
                body = response.read(MAX_FEED_BYTES + 1)
        except (urllib.error.URLError, TimeoutError, OSError):
            raise ValueError("Configured event feed could not be reached.") from None
        if (
            len(body) > MAX_FEED_BYTES
            or b"<!DOCTYPE" in body.upper()
            or b"<!ENTITY" in body.upper()
        ):
            raise ValueError("Feed is oversized or contains unsupported XML declarations.")
        try:
            root = ET.fromstring(body)
        except ET.ParseError:
            raise ValueError("Event feed XML is invalid.") from None

        def local(tag):
            return tag.rsplit("}", 1)[-1].casefold()

        entries = [node for node in root.iter() if local(node.tag) in {"item", "entry"}]
        result = []
        for entry in entries[:MAX_FEED_ITEMS]:
            values = {
                local(node.tag): (node.text or "").strip()
                for node in entry.iter()
                if len(node) == 0
            }
            link = values.get("link", "")
            if not link:
                link_node = next((node for node in entry if local(node.tag) == "link"), None)
                link = link_node.attrib.get("href", "") if link_node is not None else ""
            timestamp = values.get("published") or values.get("updated") or values.get("pubdate")
            try:
                observed = (
                    datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    if timestamp and "T" in timestamp
                    else parsedate_to_datetime(timestamp)
                    if timestamp
                    else datetime.now(UTC)
                )
                if observed.tzinfo is None or observed.utcoffset() is None:
                    observed = observed.replace(tzinfo=UTC)
            except ValueError:
                observed = datetime.now(UTC)
            title = html.unescape(values.get("title", "")).strip()
            description = html.unescape(values.get("description", values.get("summary", "")))
            link = link or values.get("id", "")
            if title and link:
                result.append(
                    FeedItem(
                        id=link[:2048],
                        title=title[:256],
                        description=re.sub(r"<[^>]{0,256}>", " ", description)[:10000],
                        observed_at=observed,
                    )
                )
        return result


class GDELTFeed:
    """Bounded GDELT DOC ArticleList adapter that consumes its documented RSS mode."""

    HOST = "api.gdeltproject.org"

    def __init__(
        self,
        query: str,
        allowed_hosts: set[str],
        *,
        timespan: str = "24h",
        max_records: int = 50,
        timeout: float = 10,
    ):
        if not isinstance(query, str) or not query.strip() or len(query) > 256:
            raise ValueError("GDELT query must contain 1 to 256 characters.")
        duration = (
            re.fullmatch(r"(\d{1,3})(min|h|d|w|m)", timespan) if isinstance(timespan, str) else None
        )
        if duration is None:
            raise ValueError("GDELT timespan must be a bounded duration such as 24h or 7d.")
        amount, unit = int(duration.group(1)), duration.group(2)
        duration_minutes = amount * {"min": 1, "h": 60, "d": 1440, "w": 10080, "m": 43200}[unit]
        if duration_minutes < 15 or duration_minutes > 129600:
            raise ValueError("GDELT timespan must be at least 15 minutes and at most 90 days.")
        if (
            isinstance(max_records, bool)
            or not isinstance(max_records, int)
            or not 1 <= max_records <= 75
        ):
            raise ValueError("GDELT max_records must be between 1 and 75.")
        if self.HOST not in {host.casefold().rstrip(".") for host in allowed_hosts}:
            raise ValueError("GDELT host must be added to the event feed allowlist.")
        query_string = urllib.parse.urlencode(
            {
                "query": query,
                "mode": "artlist",
                "format": "rss",
                "timespan": timespan,
                "maxrecords": max_records,
                "sort": "datedesc",
            }
        )
        url = f"https://{self.HOST}/api/v2/doc/doc?{query_string}"
        self.reader = RSSFeed(url, allowed_hosts, timeout=timeout)

    def read(self) -> list[FeedItem]:
        return self.reader.read()


def configured_feeds(tenant_id: str) -> list[dict]:
    path = os.environ.get("SUBSTRATA_EVENT_FEEDS_FILE")
    if not path:
        return []
    try:
        values = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise ValueError("Configured event feed file is invalid.") from None
    if not isinstance(values, list) or len(values) > 10:
        raise ValueError("Event feed configuration must be a list of at most 10 feeds.")
    return [
        item for item in values if isinstance(item, dict) and item.get("tenant_id") == tenant_id
    ]


def subscription(store, actor, rule: EventRule, name: str = "default"):
    actor.require("admin")
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,96}", name):
        raise ValueError("Subscription name is invalid.")
    tenant = actor.tenant_id
    id = f"subscription-{name}"
    with tenant_transaction(store.engine, tenant) as session:
        org = store.organisation(session, tenant)
        record = session.get(WorkRecord, (tenant, id))
        if record is None:
            record = add(
                session,
                tenant,
                "event_subscription",
                "active" if rule.enabled else "disabled",
                rule.model_dump(mode="json"),
                id,
            )
        else:
            record.payload = rule.model_dump(mode="json")
            record.status = "active" if rule.enabled else "disabled"
        store.append(
            session,
            org,
            "event.subscription.updated",
            actor.subject,
            {
                "id": id,
                "categories": sorted(rule.categories),
                "minimum_severity": rule.minimum_severity,
            },
        )
        return encode(record)


def classify(title: str, description: str):
    text = f"{title} {description}".casefold()
    rules = (
        ("sanctions", ("sanction", "export control", "restricted party", "embargo")),
        ("weather", ("flood", "storm", "earthquake", "wildfire", "hurricane", "typhoon")),
        ("transport", ("port closure", "congestion", "canal", "shipping delay", "strike")),
        (
            "supply_disruption",
            ("factory closure", "production halt", "recall", "shortage", "outage", "disruption"),
        ),
    )
    category, terms = next(
        ((kind, terms) for kind, terms in rules if any(term in text for term in terms)),
        ("other", ()),
    )
    severity = min(1.0, 0.3 + 0.2 * sum(term in text for term in terms)) if terms else 0.2
    return category, round(severity, 2), "keyword_rules-v1"


def match_entities(store, tenant_id, title: str, description: str):
    from substrata.platform.models import Organisation

    with tenant_transaction(store.engine, tenant_id) as session:
        org = session.get(Organisation, tenant_id)
        if org is None:
            raise ValueError("Organisation is unavailable.")
        if org.version == 0:
            return []
    snapshot = store.snapshot(tenant_id)
    haystack = f" {re.sub(r'[^\w]+', ' ', f'{title} {description}'.casefold()).strip()} "
    candidates = []
    for entity in snapshot.data.entities:
        name = f" {re.sub(r'[^\w]+', ' ', entity.name.casefold()).strip()} "
        score = (
            1.0
            if name.strip() and name in haystack
            else SequenceMatcher(None, name.strip(), haystack.strip()).ratio()
        )
        if score >= 0.35:
            candidates.append(
                {
                    "entity_id": entity.id,
                    "name": entity.name,
                    "confidence": round(score, 3),
                    "provenance": entity.provenance.model_dump(mode="json"),
                }
            )
    return sorted(candidates, key=lambda item: (-item["confidence"], item["entity_id"]))[:5]


def _has_confident_match(matches):
    return bool(
        matches
        and matches[0]["confidence"] >= 0.85
        and (len(matches) == 1 or matches[0]["confidence"] - matches[1]["confidence"] >= 0.15)
    )


def ingest(store, tenant_id: str, submitted: EventSubmission):
    category, severity, classifier = classify(submitted.title, submitted.description)
    canonical_id = hashlib.sha256(
        f"{submitted.provenance.uri}|{submitted.source_id}".encode()
    ).hexdigest()
    event_id = f"event-{canonical_id}"
    matches = match_entities(store, tenant_id, submitted.title, submitted.description)
    event = {
        **submitted.model_dump(mode="json"),
        "category": category,
        "severity": {
            "value": severity,
            "unit": "fraction",
            "provenance": {
                "uri": submitted.provenance.uri,
                "observed_at": submitted.provenance.observed_at.isoformat(),
                "kind": "assumption",
                "note": f"Deterministic {classifier}; heuristic severity, not a probability.",
            },
        },
        "classification": {
            "value": category,
            "confidence": {
                "value": 0.8 if category != "other" else 0.4,
                "unit": "fraction",
                "provenance": {
                    "uri": "rules://event-classification-v1",
                    "observed_at": submitted.observed_at.isoformat(),
                    "kind": "assumption",
                    "note": "Heuristic classification confidence; not a calibrated probability.",
                },
            },
        },
        "matches": matches,
    }
    with tenant_transaction(store.engine, tenant_id) as session:
        org = store.organisation(session, tenant_id)
        existing = session.get(WorkRecord, (tenant_id, event_id))
        if existing:
            return encode(existing)
        record = add(
            session,
            tenant_id,
            "event",
            "matched" if _has_confident_match(matches) else "needs_review",
            event,
            event_id,
        )
        for rule_record in session.scalars(select_event_subscriptions(tenant_id)):
            rule = EventRule.model_validate(rule_record.payload)
            if rule.enabled and category in rule.categories and severity >= rule.minimum_severity:
                alert_id = (
                    f"alert-{hashlib.sha256(f'{event_id}|{rule_record.id}'.encode()).hexdigest()}"
                )
                if session.get(WorkRecord, (tenant_id, alert_id)) is None:
                    add(
                        session,
                        tenant_id,
                        "alert",
                        "open",
                        {
                            "event_id": event_id,
                            "subscription_id": rule_record.id,
                            "category": category,
                            "severity": event["severity"],
                            "matches": matches,
                        },
                        alert_id,
                    )
        store.append(
            session,
            org,
            "event.ingested",
            "feed",
            {
                "id": event_id,
                "source": submitted.provenance.uri,
                "category": category,
                "severity": severity,
                "match_count": len(matches),
            },
        )
        return encode(record)


def select_event_subscriptions(tenant_id):
    from sqlalchemy import select

    return select(WorkRecord).where(
        WorkRecord.tenant_id == tenant_id, WorkRecord.kind == "event_subscription"
    )


def submit(store, actor, body: EventSubmission):
    actor.require("analyst")
    return ingest(store, actor.tenant_id, body)


def poll(store, tenant_id: str):
    allowed = {
        host.strip().casefold()
        for host in os.environ.get("SUBSTRATA_EVENT_ALLOWED_HOSTS", "").split(",")
        if host.strip()
    }
    feed_configs = configured_feeds(tenant_id)
    results = []
    for config in feed_configs:
        if (
            not isinstance(config.get("name"), str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,48}", config["name"])
            or not isinstance(config.get("license"), str)
            or not config["license"].strip()
        ):
            raise ValueError("Every public feed requires a name and licensing note.")
        feed_type = config.get("type", "rss")
        if feed_type == "rss":
            feed = RSSFeed(config.get("url", ""), allowed)
        elif feed_type == "gdelt":
            feed = GDELTFeed(
                config.get("query", ""),
                allowed,
                timespan=config.get("timespan", "24h"),
                max_records=config.get("max_records", 50),
            )
        else:
            raise ValueError("Configured event feed type is not supported.")
        for item in feed.read():
            provenance = Provenance(
                uri=item.id,
                observed_at=item.observed_at,
                kind="public",
                note=f"{config['name']}; licence: {config['license']}",
            )
            results.append(
                ingest(
                    store,
                    tenant_id,
                    EventSubmission(
                        source_id=(
                            f"{config['name']}:{hashlib.sha256(item.id.encode()).hexdigest()}"
                        ),
                        title=item.title,
                        description=item.description,
                        observed_at=item.observed_at,
                        provenance=provenance,
                    ),
                )
            )
    return results
