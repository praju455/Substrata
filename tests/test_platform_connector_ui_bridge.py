"""Exercise the browser's real CSV conversion against the existing import API."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from test_platform_api import KEY, headers

from scripts.mock_sap import app as mock_app
from substrata.app import create_app
from substrata.platform.auth import TokenVerifier
from substrata.platform.connectors import ConnectorConfig


def test_connector_preview_frontend_mapping_apply_and_rollback(platform, monkeypatch):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js 24 is required for the frontend/backend connector bridge check.")
    config = ConnectorConfig(
        name="synthetic-mock",
        tenant_id="alpha",
        base_url="http://127.0.0.1:8521/odata/",
        resources={"vendors": "entities"},
    )
    monkeypatch.setattr(
        "substrata.platform.connectors.configured_connectors",
        lambda tenant: {config.name: config} if tenant == "alpha" else {},
    )

    def transport(url, **kwargs):
        with TestClient(mock_app) as fixture:
            return fixture.get("/odata/entities").json()

    monkeypatch.setattr("substrata.platform.connectors.read_json", transport)
    application = create_app(
        platform_store=platform,
        auth_verifier=TokenVerifier(
            issuer="test-issuer", audience="substrata", key=KEY, algorithm="HS256"
        ),
    )
    with TestClient(application) as client:
        assert client.get("/platform/connectors", headers=headers("beta")).json() == []
        response = client.post(
            "/platform/connectors/synthetic-mock/read/vendors", headers=headers(), json={}
        )
        assert response.status_code == 200
        preview = response.json()
        assert preview["provenance"]["kind"] == "synthetic"
        converted = subprocess.run(
            [
                node,
                "--experimental-strip-types",
                "--input-type=module",
                "-e",
                "import {connectorTable} from './frontend/app/platform/connector-table.ts'; "
                "let input=''; for await (const chunk of process.stdin) input += chunk; "
                "console.log(JSON.stringify(connectorTable(JSON.parse(input))));",
            ],
            input=json.dumps(preview["rows"]),
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
            timeout=30,
            cwd=Path(__file__).resolve().parents[1],
        )
        table = json.loads(converted.stdout)
        body = {
            "filename": "synthetic-vendors.csv",
            "content_base64": table["content_base64"],
            "target": "entities",
            "mapping": {},
            "expected_version": 0,
            "provenance": preview["provenance"],
        }
        described = client.post("/platform/imports/stage", headers=headers(), json=body)
        assert described.status_code == 200
        assert described.json()["columns"] == table["columns"]
        body.update(
            mapping={"id": "id", "name": "name", "kind": "kind"},
            schema_sha256=described.json()["schema_sha256"],
        )
        staged = client.post("/platform/imports/stage", headers=headers(), json=body)
        assert staged.status_code == 200
        import_id = staged.json()["id"]
        assert staged.json()["status"] == "needs_review"
        assert (
            client.post(
                f"/platform/imports/{import_id}/apply", headers=headers(), json={}
            ).status_code
            == 409
        )
        # Similar synthetic vendor names now receive the same review as matches
        # against prior graph data. This fixture intentionally keeps them separate.
        reviewed = client.post(
            f"/platform/imports/{import_id}/resolve",
            headers=headers(),
            json={
                "reason": "Synthetic mock vendors are distinct source identities.",
                "decisions": {
                    review["incoming_id"]: None for review in staged.json()["payload"]["reviews"]
                },
            },
        )
        assert reviewed.status_code == 200
        assert (
            client.post(
                f"/platform/imports/{import_id}/apply", headers=headers(), json={}
            ).status_code
            == 200
        )
        frozen = platform.snapshot("alpha")
        assert len(frozen.data.entities) == len(preview["rows"])
        assert {entity.provenance.kind for entity in frozen.data.entities} == {"synthetic"}
        assert (
            client.post(
                f"/platform/imports/{import_id}/apply", headers=headers(), json={}
            ).status_code
            == 200
        )
        assert platform.snapshot("alpha").version == frozen.version
        rolled_back = client.post(
            f"/platform/imports/{import_id}/rollback",
            headers=headers(),
            json={"reason": "Synthetic bridge verification"},
        )
        assert rolled_back.status_code == 200
        assert platform.snapshot("alpha").data.entities == []
        assert platform.snapshot("alpha", version=frozen.version).sha256 == frozen.sha256
        assert platform.audit("alpha")["verification"]["valid"]
