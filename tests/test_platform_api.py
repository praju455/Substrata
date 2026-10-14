"""Real signed claims exercise tenant boundaries, RBAC and fail-closed auth."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient

from substrata.app import create_app
from substrata.platform.auth import RateLimiter, TokenVerifier, configured_verifier
from substrata.platform.database import build_engine, migrate
from substrata.platform.store import PlatformStore

KEY = "test-only-development-secret-at-least-32-bytes"


def token(tenant="alpha", role="admin", **changes):
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "iss": "test-issuer",
            "aud": "substrata",
            "sub": "test-user",
            "tenant_id": tenant,
            "roles": [role],
            "iat": now,
            "nbf": now,
            "exp": now + timedelta(minutes=5),
            **changes,
        },
        KEY,
        algorithm="HS256",
    )


def headers(tenant="alpha", role="admin", **changes):
    return {"Authorization": "Bearer " + token(tenant, role, **changes)}


@pytest.fixture
def client(tmp_path):
    engine = build_engine(f"sqlite:///{(tmp_path / 'api.sqlite3').as_posix()}")
    migrate(engine)
    app = create_app(
        platform_store=PlatformStore(engine),
        auth_verifier=TokenVerifier(
            issuer="test-issuer", audience="substrata", key=KEY, algorithm="HS256"
        ),
    )
    with TestClient(app) as instance:
        yield instance
    engine.dispose()


@pytest.mark.parametrize(
    "changes",
    [
        {"aud": "other"},
        {"iss": "other"},
        {"roles": ["owner"]},
        {"exp": datetime.now(UTC) - timedelta(minutes=1)},
        {"nbf": datetime.now(UTC) + timedelta(hours=1)},
    ],
)
def test_wrong_claims_fail_closed(client, changes):
    assert client.get("/platform/identity", headers=headers(**changes)).status_code == 401


def test_required_auth_and_demo_reset_absent_in_platform_mode(client):
    assert client.get("/platform/identity").status_code == 401
    assert client.post("/replay/reset").status_code == 404
    assert client.get("/health").json()["data_mode"] == "tenant"
    wrong = jwt.encode(
        {"sub": "fake"}, "a-different-secret-with-at-least-32-bytes", algorithm="HS256"
    )
    assert (
        client.get("/platform/identity", headers={"Authorization": f"Bearer {wrong}"}).status_code
        == 401
    )


def test_verified_tenant_cannot_be_overridden_and_viewer_cannot_write(client):
    for tenant in ("alpha", "beta"):
        assert (
            client.post(
                "/platform/organisation", headers=headers(tenant), json={"name": tenant}
            ).status_code
            == 201
        )
    assert (
        client.post(
            "/platform/graph", headers=headers(), json={"expected_version": 0, "data": {}}
        ).status_code
        == 200
    )
    assert (
        client.get(
            "/platform/graph", headers={**headers("beta"), "X-Tenant-ID": "alpha"}
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/platform/graph",
            headers=headers(role="viewer"),
            json={"expected_version": 1, "data": {}},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/platform/organisation", headers=headers(role="analyst"), json={"name": "Denied"}
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/platform/graph",
            headers=headers(),
            json={"expected_version": 1, "data": {}, "tenant_id": "beta"},
        ).status_code
        == 422
    )
    audit = client.get("/platform/audit", headers=headers()).json()
    assert audit["verification"]["valid"]
    assert all(r["actor"] == "test-user" for r in audit["records"])


def test_budget_returns_429_and_auth_configuration_rejects_production_hmac(
    client, monkeypatch, tmp_path
):
    client.app.state.platform_rate_limiter = RateLimiter(limit=1)
    assert client.get("/platform/identity", headers=headers()).status_code == 200
    assert client.get("/platform/identity", headers=headers()).status_code == 429
    keyfile = tmp_path / "dev.secret"
    keyfile.write_text(KEY)
    monkeypatch.setenv("SUBSTRATA_AUTH_KEY_FILE", str(keyfile))
    monkeypatch.setenv("SUBSTRATA_AUTH_ALGORITHM", "HS256")
    monkeypatch.setenv("SUBSTRATA_ENV", "production")
    with pytest.raises(ValueError, match="development"):
        configured_verifier()
