"""Policy gates, stale/duplicate approvals and copied-chain tamper detection."""

import copy
import hashlib
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError

from substrata.actions import POLICY_VERSION, policy_evaluate, rank_mitigations
from substrata.audit import append_audit, records_in, verify_chain
from substrata.cascade import cascade
from substrata.database import build_engine, transaction, upgrade_database
from substrata.governance import current_input_hashes, decide_action
from substrata.graph import NetworkXGraphStore
from substrata.seed import AS_OF, canonical, seed_database, write_fixtures
from substrata.workflow_models import (
    ActionProposal,
    ApprovalRequest,
    AuditEvent,
    EventRecord,
    Scenario,
)


@pytest.fixture
def approval_database(tmp_path):
    write_fixtures(tmp_path)
    engine = build_engine(tmp_path / "governance.sqlite3")
    upgrade_database(engine)
    seed_database(engine, tmp_path)
    snapshot = {
        "input_hashes": current_input_hashes(engine),
        "policy_version": POLICY_VERSION,
        "dataset_version": "synthetic-v1",
    }
    with transaction(engine) as session:
        session.add(
            EventRecord(
                id="event",
                event_type="disruption",
                observed_at=AS_OF,
                ingested_at=AS_OF,
                status="MATCHED",
                payload={},
            )
        )
        session.flush()
        session.add(
            Scenario(id="scenario", event_id="event", status="AWAITING_APPROVAL", snapshot=snapshot)
        )
        session.flush()
        session.add(
            ActionProposal(
                id="action",
                scenario_id="scenario",
                kind="buffer_buy",
                title="Buffer buy",
                cost=15000,
                duration_days=7,
                risk=0.3,
                rank_score=0.2,
                policy="review",
                status="awaiting_approval",
                rationale="Synthetic cost assumption",
                payload={"external_execution": "simulated_only"},
            )
        )
        session.flush()
        session.add(
            ApprovalRequest(
                action_id="action",
                snapshot_sha256=hashlib.sha256(canonical(snapshot).encode()).hexdigest(),
                expires_at=datetime.now(UTC) + timedelta(hours=1),
                status="pending",
            )
        )
        append_audit(session, "approval_needed", "Policy", {"action_id": "action"}, AS_OF)
    yield engine
    engine.dispose()


def test_named_approval_is_simulated_and_duplicate_decision_is_rejected(approval_database):
    engine = approval_database
    result = decide_action(
        engine,
        "action",
        "Demo planner",
        "planning_approver",
        "approved",
        "Protect the synthetic assembly plan",
        current_input_hashes(engine),
    )
    assert result["external_execution"] == "simulated_only"
    with transaction(engine) as session:
        assert session.get(ActionProposal, "action").status == "simulated"
        records = records_in(session)
        assert verify_chain(records)["valid"]
        assert records[-2]["actor"] == "Demo planner"
    with pytest.raises(ValueError, match="already decided"):
        decide_action(
            engine,
            "action",
            "Demo planner",
            "planning_approver",
            "approved",
            "Again",
            current_input_hashes(engine),
        )


def test_stale_snapshot_expires_approval_and_records_reason(approval_database):
    current = current_input_hashes(approval_database)
    current["graph_sha256"] = "changed"
    with pytest.raises(ValueError, match="expired"):
        decide_action(
            approval_database,
            "action",
            "Planner",
            "planning_approver",
            "approved",
            "Reason",
            current,
        )
    with transaction(approval_database) as session:
        assert session.get(ApprovalRequest, "action").status == "expired"
        assert records_in(session)[-1]["event_type"] == "approval_expired"


def test_missing_name_role_or_reason_cannot_approve(approval_database):
    for name, role, reason in [
        (" ", "planning_approver", "Reason"),
        ("Planner", "viewer", "Reason"),
        ("Planner", "planning_approver", " "),
    ]:
        with pytest.raises(ValueError, match="named approver"):
            decide_action(
                approval_database,
                "action",
                name,
                role,
                "approved",
                reason,
                current_input_hashes(approval_database),
            )


def test_chain_detects_mutation_missing_middle_and_anchored_truncation(approval_database):
    with transaction(approval_database) as session:
        append_audit(session, "second", "Agent", {"reason": "Synthetic decision"}, AS_OF)
        append_audit(session, "third", "Agent", {"reason": "Final decision"}, AS_OF)
        records = records_in(session)
    damaged = copy.deepcopy(records)
    damaged[1]["payload"]["reason"] = "tampered"
    assert not verify_chain(damaged)["valid"]
    assert not verify_chain([records[0], records[2]])["valid"]
    assert not verify_chain(records[:-1], expected_head=records[-1]["payload_hash"])["valid"]
    with pytest.raises(IntegrityError), transaction(approval_database) as session:
        session.execute(delete(AuditEvent))


def test_policy_defaults_block_and_switches_require_review(approval_database):
    snapshot = NetworkXGraphStore(approval_database).snapshot()
    result = cascade(approval_database, snapshot, "site_t1_0", 0.9)
    assert policy_evaluate("buffer_buy", 15000, result, 10000) == "review"
    assert policy_evaluate("alternate_qualification", 1, result, 10000) == "review"
    assert policy_evaluate("live_purchase_order", 1, result, 10000) == "block"
    assert policy_evaluate("expedite", 6000, result, 10000) == "record_preview"
    result.impacts[0].status = "incomplete"
    assert all(action.policy == "block" for action in rank_mitigations(result))
