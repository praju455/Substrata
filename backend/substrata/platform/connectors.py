"""Configured read-only adapters. Credentials and endpoints stay on the server."""

import hashlib
import hmac
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from fastapi import HTTPException
from opentelemetry.trace import SpanKind
from pydantic import Field

from substrata.observability import operation_span, outbound_headers
from substrata.platform.database import tenant_transaction
from substrata.platform.domain import Contract, GraphData, Provenance
from substrata.platform.models import WorkRecord
from substrata.platform.records import add, encode
from substrata.platform.store import Conflict
from substrata.seed import canonical


class Connector(Protocol):
    def read(self, resource: str) -> list[dict]: ...


class ConnectorConfig(Contract):
    name: str
    tenant_id: str
    base_url: str
    resources: dict[str, str]
    credential_file: str | None = None
    webhook_secret_file: str | None = None
    timeout_seconds: float = Field(default=10, gt=0, le=60)
    max_pages: int = Field(default=20, ge=1, le=100)
    synthetic: bool = False


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Connector redirects are refused to protect credentials.")


def read_json(url: str, *, headers=None, timeout=10):
    with operation_span(
        "connector.read", kind=SpanKind.CLIENT, attributes={"http.request.method": "GET"}
    ) as span:
        return _read_json(url, headers=headers, timeout=timeout, span=span)


def _read_json(url, *, headers, timeout, span):
    opener = urllib.request.build_opener(NoRedirect())
    try:
        request = urllib.request.Request(
            url, headers={"Accept": "application/json", **outbound_headers(headers)}
        )
        with opener.open(request, timeout=timeout) as response:
            span.set_attribute("http.response.status_code", getattr(response, "status", 200))
            body = response.read(3_000_001)
        if len(body) > 3_000_000:
            raise ValueError("Connector response exceeds 3 MB.")
        return json.loads(body)
    except urllib.error.HTTPError as exc:
        span.set_attribute("http.response.status_code", exc.code)
        exc.close()
        raise ValueError("Connector request failed; check endpoint/configuration.") from None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        raise ValueError("Connector request failed; check endpoint/configuration.") from None


class S4HANAODataConnector:
    """GET-only configurable OData v2/v4 reader with bounded pagination."""

    def __init__(self, config: ConnectorConfig):
        self.config = config
        self.synthetic = config.synthetic
        parsed = urllib.parse.urlsplit(config.base_url)
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("Connector URL must not embed credentials, query or fragment.")
        local = parsed.hostname in {"127.0.0.1", "localhost", "::1"}
        if parsed.scheme != "https" and not (
            local
            and parsed.scheme == "http"
            and os.environ.get("SUBSTRATA_ENV", "development") == "development"
        ):
            raise ValueError("Connector requires HTTPS; local mock HTTP is development-only.")
        self.origin = (parsed.scheme, parsed.hostname, parsed.port)

    def read(self, resource):
        if resource not in self.config.resources:
            raise ValueError("Resource is not configured for this adapter.")
        path = self.config.resources[resource]
        url = urllib.parse.urljoin(self.config.base_url.rstrip("/") + "/", path)
        rows, seen = [], set()
        headers = {}
        if self.config.credential_file:
            headers["Authorization"] = Path(self.config.credential_file).read_text().strip()
        for _ in range(self.config.max_pages):
            parsed = urllib.parse.urlsplit(url)
            if (
                (parsed.scheme, parsed.hostname, parsed.port) != self.origin
                or parsed.username
                or parsed.password
            ):
                raise ValueError("OData pagination must stay on the configured origin.")
            if url in seen:
                raise ValueError("OData pagination loop detected.")
            seen.add(url)
            result = read_json(url, headers=headers, timeout=self.config.timeout_seconds)
            if not isinstance(result, dict):
                raise ValueError("OData response must be an object.")
            self.synthetic |= result.get("synthetic") is True
            envelope = result.get("d", result)
            page = envelope.get("results", envelope.get("value"))
            if not isinstance(page, list) or not all(isinstance(row, dict) for row in page):
                raise ValueError("OData response requires a record array.")
            rows.extend(page)
            if len(rows) > 10000:
                raise ValueError("Connector exceeds 10000 records per import.")
            next_link = envelope.get("__next", envelope.get("@odata.nextLink"))
            if not next_link:
                return rows
            url = urllib.parse.urljoin(url, next_link)
        raise ValueError("OData pagination exceeds the configured page budget.")


class AribaAdapter:
    """Explicit integration stub; no synthetic substitute is presented as SAP data."""

    def read(self, resource):
        raise NotImplementedError(
            "SAP Business Network/Ariba access and tenant mappings are required."
        )


def configured_connectors(tenant_id):
    path = os.environ.get("SUBSTRATA_CONNECTORS_FILE")
    if not path:
        return {}
    configs = [
        ConnectorConfig.model_validate(value) for value in json.loads(Path(path).read_text())
    ]
    return {config.name: config for config in configs if config.tenant_id == tenant_id}


def receive_graph(
    store, actor, data: GraphData, expected_version: int, key: str, *, connector="rest"
):
    actor.require("analyst")
    if not key.strip() or len(key) > 96:
        raise ValueError("A bounded idempotency key is required.")
    digest = hashlib.sha256(canonical(data.model_dump(mode="json")).encode()).hexdigest()
    record_id = "rest-" + hashlib.sha256(key.encode()).hexdigest()
    with tenant_transaction(store.engine, actor.tenant_id) as session:
        org = store.organisation(session, actor.tenant_id)
        previous = session.get(WorkRecord, (actor.tenant_id, record_id))
        if previous:
            if previous.payload["sha256"] != digest:
                raise Conflict("Idempotency key was already used with different content.")
            return encode(previous)
        snapshot = store.save_in(
            session,
            org,
            data,
            actor.subject,
            expected_version=expected_version,
            event_type="connector.imported",
        )
        record = add(
            session,
            actor.tenant_id,
            "import",
            "applied",
            {
                "connector": connector,
                "sha256": digest,
                "applied_version": snapshot.version,
                "before_version": expected_version,
                "source": "authenticated REST/webhook",
            },
            record_id,
        )
        return encode(record)


def verify_webhook(tenant_id, connector, body: bytes, signature: str):
    config = configured_connectors(tenant_id).get(connector)
    if config is None or not config.webhook_secret_file:
        raise HTTPException(404, "Webhook connector is not configured.")
    key = Path(config.webhook_secret_file).read_bytes().strip()
    if len(key) < 32:
        raise ValueError("Webhook signing secret must contain at least 32 bytes.")
    expected = hmac.new(key, body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(401, "Webhook signature is invalid.")


def connector_source(config, resource, *, synthetic=False):
    return Provenance(
        uri=urllib.parse.urljoin(config.base_url.rstrip("/") + "/", config.resources[resource]),
        observed_at=datetime.now(UTC),
        kind="synthetic" if config.synthetic or synthetic else "connector",
        note="Read-only OData import; synthetic mock data."
        if config.synthetic or synthetic
        else "Read-only OData import. Confirm tenant field/unit mapping before apply.",
    )
