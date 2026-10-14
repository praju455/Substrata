"""Single-use signatures, tenant binding, immutable history and training labels."""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from cryptography.fernet import Fernet
from test_platform_evidence import actor, prepare

from substrata.platform.confirmations import (
    ConfirmationInput,
    PortalSigner,
    SupplierReply,
    create_request,
    describe_request,
    reply,
)
from substrata.platform.notifications import SMTPMailer, deliver_pending_confirmations
from substrata.platform.records import list_records
from substrata.platform.store import Conflict

SIGNER = PortalSigner("test-confirmation-secret-with-at-least-32-bytes")


def test_smtp_mailer_uses_implicit_tls_and_secret_file(monkeypatch, tmp_path):
    password_file = tmp_path / "smtp.secret"
    password_file.write_text("test-password\n", encoding="utf-8")
    monkeypatch.setenv("SUBSTRATA_SMTP_HOST", "mail.example.test")
    monkeypatch.setenv("SUBSTRATA_SMTP_PORT", "465")
    monkeypatch.setenv("SUBSTRATA_SMTP_FROM", "Substrata <alerts@example.test>")
    monkeypatch.setenv("SUBSTRATA_SMTP_USERNAME", "mailer-user")
    monkeypatch.setenv("SUBSTRATA_SMTP_PASSWORD_FILE", str(password_file))
    connection = Mock()
    context = Mock()
    context.__enter__ = Mock(return_value=connection)
    context.__exit__ = Mock(return_value=False)
    smtp_ssl = Mock(return_value=context)
    monkeypatch.setattr("smtplib.SMTP_SSL", smtp_ssl)

    SMTPMailer().send("supplier@example.test", "Confirm relationship", "Review link", "message-123")

    smtp_ssl.assert_called_once()
    assert smtp_ssl.call_args.args[:2] == ("mail.example.test", 465)
    assert smtp_ssl.call_args.kwargs["timeout"] == 15
    assert smtp_ssl.call_args.kwargs["context"] is not None
    connection.login.assert_called_once_with("mailer-user", "test-password")
    message = connection.send_message.call_args.args[0]
    assert message["To"] == "supplier@example.test"
    assert message["Subject"] == "Confirm relationship"
    assert message["Message-ID"]


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


def test_supplier_confirmation_email_is_tls_worker_delivery_and_dev_stays_disabled(
    platform, monkeypatch, tmp_path
):
    from substrata.platform.confirmations import ConfirmationInput, create_request
    from substrata.platform.evidence import discover

    prepare(platform)
    discover(platform, actor(), "Alpha Supplier")
    link = platform.snapshot("alpha").data.links[0]
    key_path = tmp_path / "pii.secret"
    key_path.write_bytes(Fernet.generate_key())
    monkeypatch.setenv("SUBSTRATA_PII_KEY_FILE", str(key_path))
    monkeypatch.setenv("SUBSTRATA_CONFIRMATION_KEY_FILE", str(key_path))
    monkeypatch.setenv("SUBSTRATA_PORTAL_URL", "https://portal.example.test/confirm/")
    monkeypatch.setenv("SUBSTRATA_ENV", "production")
    created = create_request(
        platform,
        actor(),
        ConfirmationInput(link_id=link.id, recipient_email="supplier@example.test"),
        signer=SIGNER,
    )
    assert created["delivery_queued"] is True
    from substrata.platform.database import tenant_transaction
    from substrata.platform.models import WorkRecord

    with tenant_transaction(platform.engine, "alpha") as session:
        request_record = session.get(WorkRecord, ("alpha", created["request"]["id"]))
        request_record.payload = {
            **request_record.payload,
            "remind_after": (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
        }

    class Mailer:
        messages = []

        def send(self, recipient, subject, body, message_id):
            self.messages.append((recipient, subject, body, message_id))

    mailer = Mailer()
    result = deliver_pending_confirmations(platform, actor(), mailer=mailer)
    assert result == {"delivered": 2, "attempted": 2, "status": "processed"}
    assert mailer.messages[0][0] == "supplier@example.test"
    assert "https://portal.example.test/confirm/#token=" in mailer.messages[0][2]
    assert mailer.messages[0][3]
    assert "https://portal.example.test/confirm/#token=" in mailer.messages[1][2]
    assert mailer.messages[0][3] != mailer.messages[1][3]
    notifications = list_records(platform, "alpha", kind="notification")
    delivered = next(
        item for item in notifications if item["payload"]["type"] == "supplier_confirmation"
    )
    assert delivered["status"] == "delivered"
    assert "recipient_ciphertext" not in delivered["payload"]
    assert platform.audit("alpha")["verification"]["valid"]

    retry_request = create_request(
        platform,
        actor(),
        ConfirmationInput(link_id=link.id, recipient_email="retry-supplier@example.test"),
        signer=SIGNER,
    )

    class FailingMailer:
        def send(self, *args):
            raise TimeoutError("private SMTP diagnostic")

    retried = deliver_pending_confirmations(platform, actor(), mailer=FailingMailer())
    assert retried == {"delivered": 0, "attempted": 1, "status": "processed"}
    pending = next(
        item
        for item in list_records(platform, "alpha", kind="notification")
        if item["payload"].get("request_id") == retry_request["request"]["id"]
    )
    assert pending["status"] == "pending"
    assert pending["payload"]["attempts"] == 1
    assert pending["payload"]["last_error_type"] == "TimeoutError"
    assert "private SMTP diagnostic" not in str(pending)

    monkeypatch.setenv("SUBSTRATA_ENV", "development")
    create_request(
        platform,
        actor(),
        ConfirmationInput(link_id=link.id, recipient_email="dev-supplier@example.test"),
        signer=SIGNER,
    )
    disabled = deliver_pending_confirmations(platform, actor(), mailer=mailer)
    assert disabled == {"delivered": 0, "status": "development_disabled"}
    assert len(mailer.messages) == 2
