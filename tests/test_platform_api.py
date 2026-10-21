"""Real signed claims exercise tenant boundaries, RBAC and fail-closed auth."""

import json
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


def test_read_only_assistant_endpoint_works_without_uploaded_documents(client):
    from substrata.platform.seeds import generate

    store = client.app.state.platform_store
    store.provision("alpha", "Alpha", "admin")
    store.save("alpha", generate("automotive"), "admin", expected_version=0)
    before = store.snapshot("alpha")
    denied = client.post(
        "/platform/assistant/ask",
        json={"question": "Which supplier dependency affects the plant?", "web_search": "off"},
    )
    assert denied.status_code == 401
    result = client.post(
        "/platform/assistant/ask",
        headers=headers(role="viewer"),
        json={"question": "Which supplier dependency affects the plant?", "web_search": "off"},
    )
    assert result.status_code == 200
    assert result.json()["read_only"] is True
    assert result.json()["retrieval"]["vector_database_used"] is False
    assert store.snapshot("alpha").sha256 == before.sha256


def test_identity_review_requires_complete_authorized_choices_before_apply(client):
    from test_platform_ingestion import upload
    from test_platform_store import graph

    store = client.app.state.platform_store
    store.provision("alpha", "Alpha", "admin")
    store.provision("beta", "Beta", "admin")
    original = store.save("alpha", graph("Acme Pharma"), "admin", expected_version=0)
    body = upload(
        "ID,Name,Type\nmerge-me,ACME PHARMA,Supplier\nkeep-me,Acme Pharma,Supplier\n",
        version=1,
    ).model_dump(mode="json")
    staged = client.post("/platform/imports/stage", json=body, headers=headers()).json()
    assert staged["status"] == "needs_review"
    path = f"/platform/imports/{staged['id']}/resolve"
    reviewed = {
        "reason": "Reviewed source identifiers: one match and one distinct supplier.",
        "decisions": {"merge-me": "supplier", "keep-me": None},
    }
    assert client.post(path, json=reviewed, headers=headers(role="viewer")).status_code == 403
    assert client.post(path, json=reviewed, headers=headers("beta")).status_code == 409
    for invalid in (
        {**reviewed, "reason": " "},
        {**reviewed, "decisions": {"merge-me": "supplier"}},
        {**reviewed, "decisions": {"merge-me": "unreviewed", "keep-me": None}},
    ):
        assert client.post(path, json=invalid, headers=headers()).status_code == 409
    assert store.snapshot("alpha").sha256 == original.sha256
    resolved = client.post(path, json=reviewed, headers=headers(role="analyst"))
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "staged"
    assert resolved.json()["payload"]["resolution"] == reviewed["decisions"]
    assert store.snapshot("alpha").sha256 == original.sha256
    applied = client.post(
        f"/platform/imports/{staged['id']}/apply", json={}, headers=headers(role="analyst")
    )
    assert applied.status_code == 200
    assert {entity.id for entity in store.snapshot("alpha").data.entities} == {
        "supplier",
        "keep-me",
    }
    assert store.snapshot("alpha", version=1).sha256 == original.sha256
    assert store.audit("alpha")["verification"]["valid"]


def test_required_auth_and_demo_reset_absent_in_platform_mode(client, caplog):
    caplog.set_level("INFO", logger="substrata.http")
    assert client.get("/platform/identity").status_code == 401
    assert client.post("/replay/reset").status_code == 404
    assert client.get("/health").json()["data_mode"] == "tenant"
    ready = client.get("/ready", headers={"X-Request-ID": "smoke-123"})
    assert ready.status_code == 200
    assert ready.headers["X-Request-ID"] == "smoke-123"
    assert client.get("/metrics").text.startswith("# HELP substrata_http_requests_total")
    assert '"event":"http.request"' in caplog.text
    logged = [json.loads(line) for line in caplog.messages if '"event":"http.request"' in line]
    assert any(entry["request_id"] == "smoke-123" for entry in logged)
    assert all("Authorization" not in line for line in caplog.messages)
    wrong = jwt.encode(
        {"sub": "fake"}, "a-different-secret-with-at-least-32-bytes", algorithm="HS256"
    )
    assert (
        client.get("/platform/identity", headers={"Authorization": f"Bearer {wrong}"}).status_code
        == 401
    )


def test_scoped_record_pagination_and_graph_aware_quality_are_available(client):
    from substrata.platform.database import tenant_transaction
    from substrata.platform.models import WorkRecord
    from substrata.platform.records import add
    from substrata.platform.seeds import generate

    store = client.app.state.platform_store
    store.provision("alpha", "Alpha", "test-admin")
    data = generate("automotive")
    store.save(
        "alpha",
        data.model_copy(update={"inventory": []}),
        "test-admin",
        expected_version=0,
    )
    with tenant_transaction(store.engine, "alpha") as session:
        for index in range(3):
            add(session, "alpha", "import", "staged", {"index": index}, f"import-{index}")
        session.add(
            WorkRecord(
                tenant_id="alpha",
                id="unrelated",
                kind="event",
                status="open",
                created_at=datetime.now(UTC),
                payload={},
            )
        )
    first = client.get(
        "/platform/records/page?kind=import&limit=2", headers=headers(role="viewer")
    ).json()
    assert [row["id"] for row in first["items"]] == ["import-2", "import-1"]
    second = client.get(
        "/platform/records/page",
        params={"kind": "import", "limit": 2, "cursor": first["next_cursor"]},
        headers=headers(role="viewer"),
    ).json()
    assert [row["id"] for row in second["items"]] == ["import-0"]
    state = client.get("/platform/state", headers=headers(role="viewer")).json()
    assert state["quality"]["inventory"]["expected_rows"] == 1
    assert state["quality"]["inventory"]["missing_row_count"] == 1


def test_readiness_fails_when_database_cannot_connect(client, monkeypatch):
    engine = client.app.state.platform_store.engine

    def unavailable():
        raise OSError("database unavailable")

    monkeypatch.setattr(engine, "connect", unavailable)
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["detail"]["dependencies"]["platform_database"] == "OSError"


def test_agent_card_and_mcp_tools_keep_exposure_deterministic_and_authenticated(client):
    store = client.app.state.platform_store
    store.provision("alpha", "Alpha", "test-admin")
    data = __import__("substrata.platform.seeds", fromlist=["generate"]).generate("pharma")
    store.save("alpha", data, "test-admin", expected_version=0)
    card = client.get("/.well-known/agent.json").json()
    assert card["url"].endswith("/platform/a2a")
    assert {
        "mapper-discovery",
        "sensor-event",
        "cascade-caller",
        "action-draft",
        "compliance-audit",
        "risk-review",
    } <= {skill["id"] for skill in card["skills"]}
    assert (
        client.post(
            "/platform/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
        ).status_code
        == 401
    )
    listed = client.post(
        "/platform/mcp",
        headers=headers(role="viewer"),
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
    ).json()
    names = {tool["name"] for tool in listed["result"]["tools"]}
    assert {
        "cascade.assess",
        "graph.snapshot",
        "audit.verify",
        "event.submit",
        "evidence.discover",
        "mitigation.propose",
        "approval.decide",
    } <= names
    graph = client.post(
        "/platform/mcp",
        headers=headers(role="viewer"),
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "graph.snapshot", "arguments": {"version": 1}},
        },
    ).json()
    assert graph["result"]["structuredContent"]["version"] == 1
    result = client.post(
        "/platform/mcp",
        headers=headers(role="analyst"),
        json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "cascade.assess",
                "arguments": {
                    "source_id": "upstream",
                    "severity": 0.8,
                    "as_of": datetime.now(UTC).isoformat(),
                },
            },
        },
    ).json()
    assert result["result"]["structuredContent"]["graph_version"] == 1
    assert result["result"]["isError"] is False


def test_a2a_assessment_is_typed_and_tenant_scoped(client):
    store = client.app.state.platform_store
    store.provision("alpha", "Alpha", "test-admin")
    data = __import__("substrata.platform.seeds", fromlist=["generate"]).generate("food")
    store.save("alpha", data, "test-admin", expected_version=0)
    response = client.post(
        "/platform/a2a",
        headers=headers(tenant="beta", role="analyst"),
        json={
            "jsonrpc": "2.0",
            "id": "rpc-1",
            "method": "tasks/send",
            "params": {
                "id": "task-1",
                "message": {
                    "role": "user",
                    "parts": [
                        {
                            "type": "data",
                            "data": {
                                "source_id": "upstream",
                                "severity": 0.6,
                                "as_of": datetime.now(UTC).isoformat(),
                            },
                        }
                    ],
                },
            },
        },
    ).json()
    assert response["error"]["code"] == -32602


def test_a2a_risk_review_queues_and_polls_tenant_scoped_checkpointed_task(client):
    store = client.app.state.platform_store
    store.provision("alpha", "Alpha", "test-admin")
    data = __import__("substrata.platform.seeds", fromlist=["generate"]).generate("pharma")
    store.save("alpha", data, "test-admin", expected_version=0)
    task_input = {
        "source_id": "upstream",
        "severity": 0.75,
        "as_of": datetime.now(UTC).isoformat(),
        "max_depth": 4,
        "graph_version": 1,
    }
    sent = client.post(
        "/platform/a2a",
        headers=headers(role="analyst"),
        json={
            "jsonrpc": "2.0",
            "id": "rpc-send",
            "method": "tasks/send",
            "params": {
                "id": "risk-review-1",
                "skillId": "risk-review",
                "message": {
                    "role": "user",
                    "parts": [{"type": "data", "data": task_input}],
                },
            },
        },
    ).json()["result"]
    assert sent["id"] == "risk-review-1"
    assert sent["status"]["state"] == "submitted"
    pending = client.post(
        "/platform/a2a",
        headers=headers(role="viewer"),
        json={
            "jsonrpc": "2.0",
            "id": "rpc-get-pending",
            "method": "tasks/get",
            "params": {"id": "risk-review-1"},
        },
    ).json()["result"]
    assert pending["status"]["state"] == "submitted"

    dispatched = client.post("/platform/jobs/dispatch", headers=headers(role="analyst"))
    assert dispatched.status_code == 200
    completed = client.post(
        "/platform/a2a",
        headers=headers(role="viewer"),
        json={
            "jsonrpc": "2.0",
            "id": "rpc-get-complete",
            "method": "tasks/get",
            "params": {"id": "risk-review-1"},
        },
    ).json()["result"]
    assert completed["status"]["state"] == "completed"
    result = completed["artifacts"][0]["parts"][0]["data"]
    assert result["checkpoints"]["cascade_caller.assessment"]["graph_version"] == 1
    assert result["checkpoints"]["compliance_audit.verification"]["valid"] is True

    elsewhere = client.post(
        "/platform/a2a",
        headers=headers(tenant="beta", role="viewer"),
        json={
            "jsonrpc": "2.0",
            "id": "rpc-get-other-tenant",
            "method": "tasks/get",
            "params": {"id": "risk-review-1"},
        },
    ).json()
    assert elsewhere["error"]["code"] == -32001


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


def test_scorer_controls_train_list_activate_and_preserve_tenant_and_role_gates(
    client, monkeypatch, tmp_path
):
    from test_platform_scoring import labels

    from substrata.platform.database import tenant_transaction
    from substrata.platform.records import add

    monkeypatch.setenv("SUBSTRATA_ENV", "development")
    monkeypatch.setenv("SUBSTRATA_MODEL_REGISTRY", str(tmp_path / "models"))
    assert (
        client.post(
            "/platform/organisation",
            headers=headers(),
            json={"name": "Synthetic scorer API fixture"},
        ).status_code
        == 201
    )
    assert (
        client.post("/platform/models/train", headers=headers(role="viewer"), json={}).status_code
        == 403
    )
    assert (
        client.post("/platform/models/train", headers=headers(role="analyst"), json={}).status_code
        == 403
    )
    insufficient = client.post("/platform/models/train", headers=headers(), json={})
    assert insufficient.status_code == 409 and "50 labels" in insufficient.json()["detail"]
    store = client.app.state.platform_store
    with tenant_transaction(store.engine, "alpha") as session:
        for label in labels():
            add(session, "alpha", "training_label", "labelled", label)
    trained = client.post("/platform/models/train", headers=headers(), json={})
    assert trained.status_code == 200
    first = trained.json()
    assert first["status"] == "candidate"
    assert first["payload"]["report"]["synthetic"] is True
    assert len(first["payload"]["model_sha256"]) == 64
    listed = client.get(
        "/platform/records?kind=model_registry", headers=headers(role="viewer")
    ).json()
    assert listed[0]["id"] == first["id"]
    assert client.get("/platform/records?kind=model_registry", headers=headers("beta")).json() == []
    route = f"/platform/models/{first['id']}/activate"
    assert client.post(route, headers=headers(role="analyst"), json={}).status_code == 403
    assert client.post(route, headers=headers("beta"), json={}).status_code == 409
    monkeypatch.setenv("SUBSTRATA_ENV", "production")
    assert client.post(route, headers=headers(), json={}).status_code == 409
    monkeypatch.setenv("SUBSTRATA_ENV", "development")
    assert client.post(route, headers=headers(), json={}).json()["status"] == "active"
    second = client.post("/platform/models/train", headers=headers(), json={}).json()
    assert (
        client.post(
            f"/platform/models/{second['id']}/activate", headers=headers(), json={}
        ).status_code
        == 200
    )
    versions = client.get("/platform/records?kind=model_registry", headers=headers()).json()
    assert {item["id"]: item["status"] for item in versions} == {
        first["id"]: "retired",
        second["id"]: "active",
    }
    assert (tmp_path / "models" / "alpha" / first["id"] / "model.joblib").is_file()
    assert client.get("/platform/audit", headers=headers()).json()["verification"]["valid"]
