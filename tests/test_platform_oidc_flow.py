"""Discovery and PKCE exchange reject unconfigured redirects and issuer drift."""

from datetime import UTC, datetime

import pytest
from fastapi import HTTPException

from substrata.platform.domain import Snapshot
from substrata.platform.exports import graph_csv
from substrata.platform.oidc import CodeExchange, exchange, login_config
from substrata.platform.seeds import generate


def test_oidc_discovery_and_redirect_policy(monkeypatch):
    login_config.cache_clear()
    monkeypatch.setenv("SUBSTRATA_OIDC_CLIENT_ID", "frontend")
    monkeypatch.setenv("SUBSTRATA_OIDC_ISSUER", "https://identity.example")
    monkeypatch.setenv("SUBSTRATA_OIDC_REDIRECT_URIS", "https://workspace.example/platform/")
    monkeypatch.setattr(
        "substrata.platform.oidc.read_json",
        lambda url: {
            "issuer": "https://identity.example",
            "authorization_endpoint": "https://identity.example/auth",
            "token_endpoint": "https://identity.example/token",
        },
    )
    assert login_config()["enabled"]
    with pytest.raises(HTTPException):
        exchange(
            CodeExchange(code="code", verifier="a" * 43, redirect_uri="https://attacker.example"),
            None,
        )
    login_config.cache_clear()
    monkeypatch.setattr(
        "substrata.platform.oidc.read_json", lambda url: {"issuer": "https://attacker.example"}
    )
    with pytest.raises(ValueError, match="issuer"):
        login_config()
    login_config.cache_clear()


def test_export_includes_sources_and_escapes_formula_fields():
    data = generate("food")
    values = data.model_dump(mode="json")
    values["links"][0]["provenance"]["uri"] = '=HYPERLINK("bad")'
    from substrata.platform.domain import GraphData

    snapshot = Snapshot(
        tenant_id="tenant",
        version=1,
        recorded_at=datetime.now(UTC),
        sha256="0" * 64,
        data=GraphData.model_validate(values),
    )
    exported = graph_csv(snapshot)
    assert "source_kind" in exported and "synthetic" in exported
    assert "'=HYPERLINK" in exported
