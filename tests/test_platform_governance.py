"""Authenticated authority, frozen inputs, policy change and execution gates."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from test_platform_store import source

from substrata.platform.auth import Principal
from substrata.platform.domain import Measure
from substrata.platform.governance import (
    Policy,
    ProposalInput,
    configure_policy,
    decide,
    delegate,
    execute,
    expire_pending_approvals,
    propose,
    save_assessment,
)
from substrata.platform.seeds import generate
from substrata.platform.store import Conflict


def actor(subject="analyst", role="analyst", tenant="alpha"):
    return Principal(subject=subject, tenant_id=tenant, roles={role})


def measure(value, unit):
    return Measure(value=value, unit=unit, provenance=source())


def prepared(platform, cost=15000):
    now = datetime.now(UTC)
    platform.save("alpha", generate("automotive", as_of=now), "analyst", expected_version=0)
    configure_policy(
        platform,
        actor("administrator", "admin"),
        Policy(
            currency="USD",
            spend_limit=measure(50000, "USD"),
            auto_approve_limit=measure(1000, "USD"),
            approval_sla=measure(24, "hour"),
        ),
    )
    assessment = save_assessment(platform, actor(), "upstream", 0.9, as_of=now)
    return propose(
        platform,
        actor(),
        ProposalInput(
            assessment_id=assessment["id"],
            kind="buffer_buy",
            title="Sourced buffer quote",
            cost=measure(cost, "USD"),
            duration=measure(7, "day"),
            rationale="Supplier quote",
        ),
    )


def test_named_authority_separation_and_dry_run_idempotency(platform):
    action = prepared(platform)
    assert action["status"] == "pending"
    with pytest.raises(HTTPException):
        decide(platform, actor(), action["id"], "approved", "Reviewed")
    with pytest.raises(ValueError, match="different person"):
        decide(platform, actor("analyst", "approver"), action["id"], "approved", "Reviewed")
    approved = decide(
        platform, actor("buyer", "approver"), action["id"], "approved", "Quote checked"
    )
    assert approved["payload"]["approval"]["actor"] == "buyer"
    result = execute(platform, actor("buyer", "approver"), action["id"])
    assert result["status"] == "dry_run"
    assert result["payload"]["execution"]["mode"] == "dry_run"
    assert execute(platform, actor("buyer", "approver"), action["id"]) == result
    assert platform.audit("alpha")["verification"]["valid"]


def test_policy_or_graph_change_expires_approval_and_other_tenant_cannot_decide(platform):
    action = prepared(platform)
    platform.save("alpha", platform.snapshot("alpha").data, "analyst", expected_version=1)
    with pytest.raises(Conflict, match="expired"):
        decide(platform, actor("buyer", "approver"), action["id"], "approved", "Reviewed")
    with pytest.raises(ValueError, match="unavailable"):
        decide(platform, actor("buyer", "approver", "beta"), action["id"], "approved", "Reviewed")


def test_delegation_rejection_and_blocked_spending(platform):
    action = prepared(platform)
    delegate(platform, actor("buyer", "approver"), action["id"], "delegate", "Covering leave")
    with pytest.raises(ValueError, match="different approver"):
        decide(platform, actor("buyer", "approver"), action["id"], "approved", "Reviewed")
    rejected = decide(
        platform,
        actor("delegate", "approver"),
        action["id"],
        "rejected",
        "Insufficient available capacity",
    )
    assert rejected["status"] == "rejected"
    with pytest.raises(Conflict):
        execute(platform, actor("delegate", "approver"), action["id"])


def test_worker_expiry_marks_sla_and_emits_portal_notification(platform):
    from substrata.platform.database import tenant_transaction
    from substrata.platform.models import WorkRecord
    from substrata.platform.records import list_records

    action = prepared(platform)
    with tenant_transaction(platform.engine, "alpha") as session:
        record = session.get(WorkRecord, ("alpha", action["id"]))
        record.payload = {
            **record.payload,
            "expires_at": (datetime.now(UTC) - timedelta(seconds=1)).isoformat(),
        }

    assert expire_pending_approvals(platform, actor("worker", "analyst")) == [action["id"]]
    assert expire_pending_approvals(platform, actor("worker", "analyst")) == []
    saved = list_records(platform, "alpha", kind="mitigation")[0]
    assert saved["status"] == "expired"
    notifications = list_records(platform, "alpha", kind="notification")
    assert any(n["payload"]["type"] == "approval_expired" for n in notifications)
    assert any(n["status"] == "expired" for n in notifications)
    assert platform.audit("alpha")["verification"]["valid"]


def test_high_cost_is_blocked_and_live_writes_are_disabled_in_development(platform, monkeypatch):
    action = prepared(platform, cost=100000)
    assert action["status"] == "blocked"
    another = propose(
        platform,
        actor(),
        ProposalInput(
            assessment_id=action["payload"]["assessment_id"],
            kind="buffer_buy",
            title="Quote",
            cost=measure(10000, "USD"),
            duration=measure(7, "day"),
            rationale="Confirmed offer",
            adapter="sap",
        ),
    )
    decide(platform, actor("buyer", "approver"), another["id"], "approved", "Checked")
    monkeypatch.setenv("SUBSTRATA_SAP_WRITES_ENABLED", "true")
    monkeypatch.setenv("SUBSTRATA_ENV", "development")
    with pytest.raises(ValueError, match="development"):
        execute(platform, actor("buyer", "approver"), another["id"])
