"""Single-use signatures, tenant binding, immutable history and training labels."""

from datetime import UTC, datetime, timedelta

import pytest
from test_platform_evidence import actor, prepare

from substrata.platform.confirmations import (
    ConfirmationInput,
    PortalSigner,
    SupplierReply,
    create_request,
    describe_request,
    reply,
)
from substrata.platform.records import list_records
from substrata.platform.store import Conflict

SIGNER = PortalSigner("test-confirmation-secret-with-at-least-32-bytes")


def request(platform):
    from substrata.platform.evidence import discover

    prepare(platform)
    discover(platform, actor(), "Alpha Supplier")
    link = platform.snapshot("alpha").data.links[0]
    created = create_request(platform, actor(), ConfirmationInput(link_id=link.id), signer=SIGNER)
    return created["portal_url"].split("#token=")[1], link


def test_supplier_reply_creates_new_revision_and_label_without_rewriting_history(platform):
    token, link = request(platform)
    before = platform.snapshot("alpha")
    description = describe_request(platform, token, signer=SIGNER)
    assert description["source"] == "Alpha Supplier"
    result = reply(
        platform,
        SupplierReply(
            token=token,
            decision="confirmed",
            responder="Supplier representative",
            reason="Verified our production source",
        ),
        signer=SIGNER,
    )
    assert result["graph_version"] == before.version + 1
    assert platform.snapshot("alpha").data.links[0].status == "confirmed"
    assert platform.snapshot("alpha", version=before.version).data.links[0].status == "inferred"
    assert list_records(platform, "alpha", kind="training_label")[0]["payload"]["label"] == 1
    with pytest.raises(Conflict, match="already"):
        reply(
            platform,
            SupplierReply(token=token, decision="rejected", responder="Someone", reason="Repeat"),
            signer=SIGNER,
        )


def test_forged_and_expired_tokens_are_rejected_and_tokens_are_not_in_inbox(platform):
    token, link = request(platform)
    with pytest.raises(ValueError, match="token"):
        describe_request(platform, token + "forged", signer=SIGNER)
    expired = SIGNER.sign("alpha", "missing", datetime.now(UTC) - timedelta(minutes=1))
    with pytest.raises(ValueError, match="expired"):
        describe_request(platform, expired, signer=SIGNER)
    assert all(
        "portal_url" not in r["payload"] and "portal_ciphertext" not in r["payload"]
        for r in list_records(platform, "alpha")
    )


def test_analyst_cannot_bypass_supplier_confirmation_and_stale_link_blocks_reply(platform):
    token, link = request(platform)
    snapshot = platform.snapshot("alpha")
    confirmed = snapshot.data.model_copy(
        update={"links": [link.model_copy(update={"status": "confirmed"})]}
    )
    with pytest.raises(ValueError, match="supplier response"):
        platform.save("alpha", confirmed, "analyst", expected_version=snapshot.version)
    changed = snapshot.data.model_copy(
        update={"links": [link.model_copy(update={"confidence": 0.2})]}
    )
    platform.save("alpha", changed, "analyst", expected_version=snapshot.version)
    with pytest.raises(Conflict, match="changed"):
        reply(
            platform,
            SupplierReply(
                token=token, decision="confirmed", responder="Supplier", reason="Verified"
            ),
            signer=SIGNER,
        )


def test_rejected_response_retains_cited_link_and_negative_label(platform):
    token, link = request(platform)
    reply(
        platform,
        SupplierReply(
            token=token,
            decision="rejected",
            responder="Supplier",
            reason="We do not use this source",
        ),
        signer=SIGNER,
    )
    latest = platform.snapshot("alpha").data.links[0]
    assert latest.status == "rejected" and latest.evidence
    assert list_records(platform, "alpha", kind="training_label")[0]["payload"]["label"] == 0
