"""Public credential endpoints stop bounded peers before provider or token work."""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request
from test_platform_api import KEY, headers

from substrata.app import create_app
from substrata.platform.auth import RateLimiter, TokenVerifier, public_request


@pytest.fixture
def app(platform):
    application = create_app(
        platform_store=platform,
        auth_verifier=TokenVerifier(
            issuer="test-issuer", audience="substrata", key=KEY, algorithm="HS256"
        ),
    )
    application.state.platform_public_rate_limiter = RateLimiter(limit=2)
    return application


def test_exchange_exhausts_before_provider_and_verifier_work(app, platform, monkeypatch, caplog):
    calls = []

    def exchange(body, verifier):
        calls.append(body.code)
        verifier.verify(body.code)
        pytest.fail("Invalid authorization code was accepted as a signed token.")

    monkeypatch.setattr("substrata.platform.oidc.exchange", exchange)
    before = platform.audit("alpha")
    with TestClient(app, client=("192.0.2.10", 50000)) as client:
        for index, expected in enumerate((401, 401, 429, 429)):
            response = client.post(
                "/platform/auth/exchange",
                headers={
                    "Authorization": f"Bearer private-header-{index}",
                    "X-Forwarded-For": f"198.51.100.{index}",
                },
                json={
                    "code": f"private-code-{index}",
                    "verifier": "a" * 43,
                    "redirect_uri": "https://workspace.example/platform/",
                },
            )
            assert response.status_code == expected
        assert response.headers["Retry-After"] == "60"
    assert calls == ["private-code-0", "private-code-1"]
    assert list(app.state.platform_public_rate_limiter.entries) == [("auth_exchange", "192.0.2.10")]
    assert not app.state.platform_rate_limiter.entries
    assert platform.audit("alpha") == before
    assert "private-header" not in caplog.text and "private-code" not in caplog.text


@pytest.mark.parametrize("operation", ["describe", "reply"])
def test_supplier_endpoints_exhaust_before_signing_key_or_token_work(
    app, platform, monkeypatch, operation, caplog
):
    calls = []

    class RejectingSigner:
        def verify(self, token):
            calls.append(("verify", token))
            raise ValueError("Supplier portal token is invalid or expired.")

    def configured_signer():
        calls.append(("key", None))
        return RejectingSigner()

    monkeypatch.setattr("substrata.platform.confirmations.configured_signer", configured_signer)
    before = {tenant: platform.audit(tenant) for tenant in ("alpha", "beta")}
    with TestClient(app, client=("192.0.2.20", 50000)) as client:
        for index, expected in enumerate((409, 409, 429, 429)):
            body = {"token": f"private-portal-token-{index}"}
            if operation == "reply":
                body.update(decision="confirmed", responder="Test responder", reason="Test reply")
            response = client.post(f"/platform/supplier-portal/{operation}", json=body)
            assert response.status_code == expected
        assert response.headers["Retry-After"] == "60"
    assert calls == [
        ("key", None),
        ("verify", "private-portal-token-0"),
        ("key", None),
        ("verify", "private-portal-token-1"),
    ]
    assert list(app.state.platform_public_rate_limiter.entries) == [
        (f"portal_{operation}", "192.0.2.20")
    ]
    assert {tenant: platform.audit(tenant) for tenant in before} == before
    assert "private-portal-token" not in caplog.text


def test_endpoint_and_transport_peers_have_independent_budgets(app, monkeypatch):
    config_calls = []
    describe_calls = []

    def config():
        config_calls.append(1)
        return {"enabled": False, "development": True}

    def describe(store, token):
        describe_calls.append(1)
        raise ValueError("Supplier portal token is invalid or expired.")

    monkeypatch.setattr("substrata.platform.oidc.login_config", config)
    monkeypatch.setattr("substrata.platform.confirmations.describe_request", describe)
    with TestClient(app, client=("192.0.2.30", 50000)) as client:
        for index, expected in enumerate((200, 200, 429)):
            assert (
                client.get(
                    "/platform/auth/config",
                    headers={
                        "X-Forwarded-For": f"198.51.100.{index}",
                        "Forwarded": f"for=198.51.100.{index}",
                        "X-Real-IP": f"198.51.100.{index}",
                    },
                ).status_code
                == expected
            )
        assert (
            client.post("/platform/supplier-portal/describe", json={"token": "invalid"}).status_code
            == 409
        )
    with TestClient(app, client=("192.0.2.31", 50000)) as client:
        assert client.get("/platform/auth/config").status_code == 200
    assert len(config_calls) == 3 and len(describe_calls) == 1


def test_public_budgets_do_not_consume_or_bypass_authenticated_tenant_budget(app, monkeypatch):
    monkeypatch.setattr(
        "substrata.platform.oidc.login_config", lambda: {"enabled": False, "development": True}
    )
    app.state.platform_rate_limiter = RateLimiter(limit=1)
    with TestClient(app) as client:
        assert client.get("/platform/auth/config").status_code == 200
        assert client.get("/platform/identity", headers=headers()).status_code == 200
        assert client.get("/platform/identity", headers=headers()).status_code == 429
        assert client.get("/platform/auth/config").status_code == 200
        assert client.get("/platform/auth/config").status_code == 429
        assert client.get("/platform/identity", headers=headers()).status_code == 429


def test_missing_transport_peer_is_shared_and_public_limiter_state_stays_bounded(monkeypatch):
    limiter = RateLimiter(limit=1, window=60, capacity=2)
    application = SimpleNamespace(state=SimpleNamespace(platform_public_rate_limiter=limiter))
    clock = [10.0]
    monkeypatch.setattr("substrata.platform.auth.time.monotonic", lambda: clock[0])

    def request(peer):
        return Request(
            {
                "type": "http",
                "client": (peer, 50000) if peer else None,
                "route": SimpleNamespace(name="auth_exchange"),
                "app": application,
            }
        )

    public_request(request(None))
    with pytest.raises(HTTPException) as exhausted:
        public_request(request(None))
    assert exhausted.value.status_code == 429
    clock[0] += 60
    public_request(request(None))
    public_request(request("192.0.2.40"))
    public_request(request("192.0.2.41"))
    assert len(limiter.entries) == 2
    assert list(limiter.entries) == [
        ("auth_exchange", "192.0.2.40"),
        ("auth_exchange", "192.0.2.41"),
    ]
