"""A real workspace spending edit must retain approval and live-inference controls."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from test_platform_api import KEY, headers
from test_platform_governance import measure

from substrata.app import create_app
from substrata.platform.auth import Principal, TokenVerifier
from substrata.platform.budgets import reserve
from substrata.platform.governance import Policy


def test_policy_frontend_spending_edit_preserves_governance_and_live_budget(platform):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js 24 is required for the frontend/backend policy bridge check.")
    initial = Policy(
        currency="EUR",
        spend_limit=measure(5000, "EUR"),
        auto_approve_limit=measure(5, "EUR"),
        approval_sla=measure(72, "hour"),
        llm_daily_budget=measure(4, "USD"),
        approver_roles={"approver"},
        require_separate_approver=True,
        allowed_kinds={"buffer_buy"},
    ).model_dump(mode="json")
    app = create_app(
        platform_store=platform,
        auth_verifier=TokenVerifier(
            issuer="test-issuer", audience="substrata", key=KEY, algorithm="HS256"
        ),
    )
    with TestClient(app) as client:
        assert client.post("/platform/policy", json=initial, headers=headers()).status_code == 200
        converted = subprocess.run(
            [
                node,
                "--experimental-strip-types",
                "--input-type=module",
                "-e",
                "import {policyDraft,editedPolicy} from './frontend/app/platform/policy-edit.ts';"
                "let input=''; for await (const chunk of process.stdin) input += chunk;"
                "const policy=JSON.parse(input); const draft={...policyDraft(policy),spend:'6000'};"
                "console.log(JSON.stringify(editedPolicy(policy,draft,{"
                "uri:'synthetic://reviewed-policy',kind:'synthetic',"
                "observed_at:'2026-10-15T00:00:00Z',note:'Invented spending revision'})));",
            ],
            input=json.dumps(initial),
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
            timeout=30,
            cwd=Path(__file__).resolve().parents[1],
        )
        body = json.loads(converted.stdout)
        for role in ("viewer", "analyst", "approver"):
            assert (
                client.post("/platform/policy", json=body, headers=headers(role=role)).status_code
                == 403
            )
        saved = client.post("/platform/policy", json=body, headers=headers())
        assert saved.status_code == 200
        stored = client.get("/platform/policy", headers=headers()).json()
        assert stored["spend_limit"]["value"] == 6000
        assert stored["spend_limit"]["provenance"]["uri"] == "synthetic://reviewed-policy"
        for field in (
            "auto_approve_limit",
            "approval_sla",
            "llm_daily_budget",
            "approver_roles",
            "require_separate_approver",
            "allowed_kinds",
        ):
            assert stored[field] == initial[field]
        assert client.get("/platform/policy", headers=headers("beta")).json() == {}
        actor = Principal(tenant_id="alpha", subject="analyst", roles={"analyst"})
        reserve(platform, actor, 3, "synthetic-regression")
        with pytest.raises(ValueError, match="exhausted"):
            reserve(platform, actor, 2, "synthetic-regression")
        assert platform.audit("alpha")["verification"]["valid"]
