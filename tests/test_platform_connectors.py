"""Read-only OData transport limits, synthetic provenance and REST dedupe."""

import json

import pytest
from fastapi.testclient import TestClient
from test_platform_store import graph

from scripts.mock_sap import app
from substrata.platform.auth import Principal
from substrata.platform.connectors import (
    AribaAdapter,
    ConnectorConfig,
    NoRedirect,
    S4HANAODataConnector,
    connector_source,
    receive_graph,
)
from substrata.platform.store import Conflict


def config():
    return ConnectorConfig(
        name="mock",
        tenant_id="alpha",
        base_url="http://127.0.0.1:8521/odata/",
        resources={"vendors": "entities"},
    )


def test_read_only_adapter_consumes_mock_and_labels_synthetic(monkeypatch):
    def transport(url, **kwargs):
        with TestClient(app) as client:
            return client.get("/odata/entities").json()

    monkeypatch.setattr("substrata.platform.connectors.read_json", transport)
    adapter = S4HANAODataConnector(config())
    assert adapter.read("vendors")[0]["kind"] == "Site"
    assert connector_source(config(), "vendors", synthetic=adapter.synthetic).kind == "synthetic"
    with pytest.raises(NotImplementedError):
        AribaAdapter().read("vendors")


def test_paginated_response_cannot_exfiltrate_credentials_or_loop(monkeypatch):
    monkeypatch.setattr(
        "substrata.platform.connectors.read_json",
        lambda *a, **k: {"value": [], "@odata.nextLink": "https://other.example/stolen"},
    )
    with pytest.raises(ValueError, match="origin"):
        S4HANAODataConnector(config()).read("vendors")
    monkeypatch.setattr(
        "substrata.platform.connectors.read_json",
        lambda *a, **k: {"value": [], "@odata.nextLink": "entities"},
    )
    with pytest.raises(ValueError, match="loop"):
        S4HANAODataConnector(config()).read("vendors")
    with pytest.raises(ValueError, match="redirect"):
        NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.example")


def test_production_refuses_cleartext_and_cross_tenant_rest_keys_are_isolated(
    platform, monkeypatch
):
    monkeypatch.setenv("SUBSTRATA_ENV", "production")
    with pytest.raises(ValueError, match="HTTPS"):
        S4HANAODataConnector(config())
    first = receive_graph(
        platform,
        Principal(subject="machine", tenant_id="alpha", roles={"analyst"}),
        graph(),
        0,
        "upload-1",
    )
    repeated = receive_graph(
        platform,
        Principal(subject="machine", tenant_id="alpha", roles={"analyst"}),
        graph().model_copy(update={"entities": platform.snapshot("alpha").data.entities}),
        0,
        "upload-1",
    )
    assert repeated["id"] == first["id"]
    with pytest.raises(Conflict, match="different content"):
        receive_graph(
            platform,
            Principal(subject="machine", tenant_id="alpha", roles={"analyst"}),
            graph("Changed"),
            1,
            "upload-1",
        )
    receive_graph(
        platform,
        Principal(subject="machine", tenant_id="beta", roles={"analyst"}),
        graph(),
        0,
        "upload-1",
    )
    assert platform.snapshot("beta").version == 1


def test_webhook_requires_signature_and_uses_tenant_config(tmp_path, monkeypatch):
    import hashlib
    import hmac

    from fastapi import HTTPException

    from substrata.platform.connectors import verify_webhook

    key = b"test-webhook-secret-with-at-least-32-bytes"
    secret = tmp_path / "webhook.secret"
    secret.write_bytes(key)
    configs = tmp_path / "connectors.json"
    configs.write_text(json.dumps([{**config().model_dump(), "webhook_secret_file": str(secret)}]))
    monkeypatch.setenv("SUBSTRATA_CONNECTORS_FILE", str(configs))
    body = b'{"example":"data"}'
    verify_webhook("alpha", "mock", body, hmac.new(key, body, hashlib.sha256).hexdigest())
    with pytest.raises(HTTPException):
        verify_webhook("alpha", "mock", body, "forged")
    with pytest.raises(HTTPException):
        verify_webhook("beta", "mock", body, "forged")
