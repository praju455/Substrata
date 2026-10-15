"""Explicit SMTP delivery for encrypted supplier and approval notifications."""

import hashlib
import json
import os
import re
import smtplib
import ssl
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from email.utils import make_msgid, parseaddr
from pathlib import Path

from sqlalchemy import select

from substrata.platform.confirmations import privacy_cipher
from substrata.platform.database import tenant_transaction
from substrata.platform.models import WorkRecord
from substrata.platform.records import add

MAX_DELIVERIES_PER_POLL = 20
MAX_ATTEMPTS = 4
RETRY_SECONDS = (5, 30, 120)
DELIVERY_LEASE = timedelta(minutes=2)


def queue_approval_email_notifications(store, session, tenant_id: str, actor_subject: str, action):
    """Encrypt optional tenant approver recipients and add auditable mail outbox rows."""
    config_path = os.environ.get("SUBSTRATA_APPROVER_EMAILS_FILE", "")
    if not config_path or os.environ.get("SUBSTRATA_ENV", "development") == "development":
        return 0
    try:
        tenants = json.loads(Path(config_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise ValueError("Approver email configuration is invalid.") from None
    if not isinstance(tenants, list) or len(tenants) > 500:
        raise ValueError("Approver email configuration must contain at most 500 tenants.")
    matches = [
        item for item in tenants if isinstance(item, dict) and item.get("tenant_id") == tenant_id
    ]
    if len(matches) > 1:
        raise ValueError("Approver email configuration contains a duplicate tenant.")
    if not matches:
        return 0
    emails = matches[0].get("emails")
    if not isinstance(emails, list) or not 1 <= len(emails) <= 10:
        raise ValueError("Configured approver email list must contain 1 to 10 addresses.")
    normalized = []
    for value in emails:
        address = parseaddr(value)[1] if isinstance(value, str) else ""
        if (
            not address
            or any(char in value for char in "\r\n")
            or not re.fullmatch(r"[^\s@<>]+@[^\s@<>]+", address)
        ):
            raise ValueError("Configured approver email address is invalid.")
        if address.casefold() not in {email.casefold() for email in normalized}:
            normalized.append(address)
    cipher = privacy_cipher()
    queued = 0
    for address in normalized:
        recipient_ciphertext = cipher.encrypt(address.encode()).decode()
        notification_id = (
            "approval-email-"
            + hashlib.sha256(f"{action.id}|{address.casefold()}".encode()).hexdigest()
        )
        if session.get(WorkRecord, (tenant_id, notification_id)) is not None:
            continue
        add(
            session,
            tenant_id,
            "notification",
            "pending",
            {
                "type": "approval_needed_email",
                "action_id": action.id,
                "title": action.payload["title"],
                "due_at": action.payload["expires_at"],
                "channel": "email",
                "recipient_ciphertext": recipient_ciphertext,
                "attempts": 0,
                "retry_at": datetime.now(UTC).isoformat(),
            },
            notification_id,
        )
        queued += 1
    if queued:
        store.append(
            session,
            store.organisation(session, tenant_id),
            "approval.email_notifications.queued",
            actor_subject,
            {"action_id": action.id, "count": queued},
        )
    return queued


class SMTPMailer:
    """SMTP-over-TLS transport configured only from deployment environment."""

    def __init__(self):
        self.host = os.environ.get("SUBSTRATA_SMTP_HOST", "")
        self.port = int(os.environ.get("SUBSTRATA_SMTP_PORT", "465"))
        sender = os.environ.get("SUBSTRATA_SMTP_FROM", "")
        self.sender = parseaddr(sender)[1]
        self.username = os.environ.get("SUBSTRATA_SMTP_USERNAME", "")
        password_file = os.environ.get("SUBSTRATA_SMTP_PASSWORD_FILE", "")
        self.password = (
            Path(password_file).read_text(encoding="utf-8").strip() if password_file else ""
        )
        if not re.fullmatch(r"[A-Za-z0-9.-]{1,253}", self.host):
            raise ValueError("A valid SMTP host is required for email delivery.")
        if not 1 <= self.port <= 65535:
            raise ValueError("SMTP port must be between 1 and 65535.")
        if (
            not self.sender
            or any(char in sender for char in "\r\n")
            or not re.fullmatch(r"[^\s@<>]+@[^\s@<>]+", self.sender)
        ):
            raise ValueError("A valid SMTP sender address is required for email delivery.")
        if bool(self.username) != bool(self.password):
            raise ValueError("SMTP username and password file must be configured together.")

    def send(self, recipient: str, subject: str, body: str, message_id: str):
        message = EmailMessage()
        message["From"] = self.sender
        message["To"] = recipient
        message["Subject"] = subject
        message["Message-ID"] = make_msgid(idstring=message_id, domain=self.sender.split("@", 1)[1])
        message.set_content(body)
        with smtplib.SMTP_SSL(
            self.host, self.port, timeout=15, context=ssl.create_default_context()
        ) as smtp:
            if self.username:
                smtp.login(self.username, self.password)
            smtp.send_message(message)


def _queue_due_reminders(store, tenant_id: str, now: datetime):
    """Create at most one deterministic reminder for each eligible request."""
    with tenant_transaction(store.engine, tenant_id) as session:
        org = store.organisation(session, tenant_id)
        requests = list(
            session.scalars(
                select(WorkRecord)
                .where(
                    WorkRecord.tenant_id == tenant_id,
                    WorkRecord.kind == "confirmation",
                    WorkRecord.status == "pending",
                    WorkRecord.payload["recipient_ciphertext"].as_string().is_not(None),
                    WorkRecord.payload["reminders_sent"].as_integer() == 0,
                    WorkRecord.payload["remind_after"].as_string() <= now.isoformat(),
                    WorkRecord.payload["expires_at"].as_string() > now.isoformat(),
                )
                .order_by(WorkRecord.created_at, WorkRecord.id)
                .limit(MAX_DELIVERIES_PER_POLL * 10)
            )
        )
        queued = 0
        for request in requests:
            payload = request.payload
            reminder_id = "confirmation-reminder-" + hashlib.sha256(request.id.encode()).hexdigest()
            if session.get(WorkRecord, (tenant_id, reminder_id)) is not None:
                continue
            original = next(
                (
                    item
                    for item in session.scalars(
                        select(WorkRecord).where(
                            WorkRecord.tenant_id == tenant_id,
                            WorkRecord.kind == "notification",
                            WorkRecord.payload["request_id"].as_string() == request.id,
                        )
                    )
                    if item.payload.get("type") == "supplier_confirmation"
                ),
                None,
            )
            if original is None or not original.payload.get("portal_ciphertext"):
                continue
            add(
                session,
                tenant_id,
                "notification",
                "pending",
                {
                    "type": "supplier_confirmation_reminder",
                    "request_id": request.id,
                    "channel": "email",
                    "recipient_ciphertext": payload["recipient_ciphertext"],
                    "portal_ciphertext": original.payload["portal_ciphertext"],
                    "attempts": 0,
                    "retry_at": now.isoformat(),
                },
                reminder_id,
            )
            queued += 1
        if queued:
            store.append(
                session,
                org,
                "confirmation.reminders.queued",
                "worker",
                {"count": queued},
            )
        return queued


def _claim(store, tenant_id: str, now: datetime):
    with tenant_transaction(store.engine, tenant_id) as session:
        query = (
            select(WorkRecord)
            .where(
                WorkRecord.tenant_id == tenant_id,
                WorkRecord.kind == "notification",
                WorkRecord.status.in_(("pending", "sending")),
            )
            .order_by(WorkRecord.created_at, WorkRecord.id)
            .with_for_update(skip_locked=True)
            .limit(MAX_DELIVERIES_PER_POLL * 10)
        )
        for notification in session.scalars(query):
            payload = notification.payload
            if payload.get("channel") != "email" or payload.get("type") not in {
                "supplier_confirmation",
                "supplier_confirmation_reminder",
                "approval_needed_email",
            }:
                continue
            if datetime.fromisoformat(payload.get("retry_at", now.isoformat())) > now:
                continue
            if (
                notification.status == "sending"
                and datetime.fromisoformat(payload.get("lease_until", now.isoformat())) > now
            ):
                continue
            if payload.get("attempts", 0) >= MAX_ATTEMPTS:
                notification.status = "failed"
                store.append(
                    session,
                    store.organisation(session, tenant_id),
                    "notification.delivery_failed",
                    "worker",
                    {"id": notification.id, "reason": "attempt_limit"},
                )
                continue
            if payload["type"] == "approval_needed_email":
                request = session.get(WorkRecord, (tenant_id, payload.get("action_id", "")))
                valid_request = (
                    request is not None
                    and request.kind == "mitigation"
                    and request.status == "pending"
                    and datetime.fromisoformat(request.payload["expires_at"]) > now
                )
            else:
                request = session.get(WorkRecord, (tenant_id, payload.get("request_id", "")))
                valid_request = (
                    request is not None
                    and request.kind == "confirmation"
                    and request.status == "pending"
                    and datetime.fromisoformat(request.payload["expires_at"]) > now
                )
            if not valid_request:
                notification.status = "expired"
                store.append(
                    session,
                    store.organisation(session, tenant_id),
                    "notification.expired",
                    "worker",
                    {
                        "id": notification.id,
                        "action_id": payload.get("action_id"),
                        "request_id": payload.get("request_id"),
                    },
                )
                continue
            notification.status = "sending"
            notification.payload = {
                **payload,
                "attempts": payload.get("attempts", 0) + 1,
                "lease_until": (now + DELIVERY_LEASE).isoformat(),
            }
            return notification.id, notification.payload
    return None


def _finish(store, tenant_id: str, notification_id: str, payload: dict, error: Exception | None):
    now = datetime.now(UTC)
    with tenant_transaction(store.engine, tenant_id) as session:
        org = store.organisation(session, tenant_id)
        notification = session.get(WorkRecord, (tenant_id, notification_id))
        if notification is None or notification.status != "sending":
            return
        if error is None:
            notification.status = "delivered"
            notification.payload = {
                **payload,
                "lease_until": None,
                "delivered_at": now.isoformat(),
            }
            if payload["type"] == "supplier_confirmation_reminder":
                request = session.get(WorkRecord, (tenant_id, payload["request_id"]))
                if request is not None and request.status == "pending":
                    request.payload = {**request.payload, "reminders_sent": 1}
            store.append(
                session,
                org,
                "notification.delivered",
                "worker",
                {"id": notification_id, "type": payload["type"]},
            )
            return
        attempts = payload["attempts"]
        failed = attempts >= MAX_ATTEMPTS
        retry_at = now + timedelta(seconds=RETRY_SECONDS[min(attempts - 1, len(RETRY_SECONDS) - 1)])
        notification.status = "failed" if failed else "pending"
        notification.payload = {
            **payload,
            "lease_until": None,
            "retry_at": retry_at.isoformat(),
            "last_error_type": type(error).__name__,
        }
        store.append(
            session,
            org,
            "notification.delivery_failed" if failed else "notification.retry_scheduled",
            "worker",
            {
                "id": notification_id,
                "attempt": attempts,
                "error_type": type(error).__name__,
                "retry_at": retry_at.isoformat(),
            },
        )


def deliver_pending_confirmations(store, actor, *, mailer=None, limit=MAX_DELIVERIES_PER_POLL):
    """Deliver queued confirmation/approval mail only in configured non-dev deployments."""
    actor.require("analyst")
    if os.environ.get("SUBSTRATA_ENV", "development") == "development":
        return {"delivered": 0, "status": "development_disabled"}
    if not 1 <= limit <= MAX_DELIVERIES_PER_POLL:
        raise ValueError(f"Delivery limit must be between 1 and {MAX_DELIVERIES_PER_POLL}.")
    _queue_due_reminders(store, actor.tenant_id, datetime.now(UTC))
    delivered = 0
    attempted = 0
    while attempted < limit:
        claimed = _claim(store, actor.tenant_id, datetime.now(UTC))
        if claimed is None:
            break
        notification_id, payload = claimed
        attempted += 1
        try:
            if mailer is None:
                mailer = SMTPMailer()
            cipher = privacy_cipher()
            recipient = cipher.decrypt(payload["recipient_ciphertext"].encode()).decode()
            if "\r" in recipient or "\n" in recipient or "@" not in recipient:
                raise ValueError("Encrypted notification recipient is invalid.")
            if payload["type"] == "approval_needed_email":
                action_id = payload["action_id"]
                with tenant_transaction(store.engine, actor.tenant_id) as session:
                    action = session.get(WorkRecord, (actor.tenant_id, action_id))
                    if action is None or action.kind != "mitigation" or action.status != "pending":
                        raise ValueError("Pending approval is no longer available.")
                    title = re.sub(r"[\r\n]+", " ", action.payload["title"])
                    due_at = action.payload["expires_at"]
                subject = "Mitigation action awaiting approval"
                body = (
                    f"A mitigation action is awaiting review: {title}\n\n"
                    f"Action ID: {action_id}\n"
                    f"Approval deadline: {due_at}\n\n"
                    "Sign in to the Substrata tenant workspace to review the frozen "
                    "assessment, policy and evidence before deciding. This email is a "
                    "notification only; it does not approve or execute the action."
                )
            elif payload["type"] == "supplier_confirmation":
                request_id = payload["request_id"]
                portal_ciphertext = payload.get("portal_ciphertext")
                with tenant_transaction(store.engine, actor.tenant_id) as session:
                    request = session.get(WorkRecord, (actor.tenant_id, request_id))
                    expires_at = request.payload["expires_at"] if request else ""
                if not portal_ciphertext:
                    raise ValueError("Encrypted supplier portal link is unavailable.")
                portal_url = cipher.decrypt(portal_ciphertext.encode()).decode()
                subject = "Please review a supplier relationship confirmation"
                body = (
                    "A supply-chain relationship involving your organisation needs review.\n\n"
                    f"Review and respond using this secure link: {portal_url}\n\n"
                    f"The link expires at {expires_at}. If you did not expect this request, "
                    "you can ignore this message."
                )
            else:
                request_id = payload["request_id"]
                portal_ciphertext = payload.get("portal_ciphertext")
                if not portal_ciphertext:
                    raise ValueError("Encrypted supplier portal link is unavailable.")
                portal_url = cipher.decrypt(portal_ciphertext.encode()).decode()
                with tenant_transaction(store.engine, actor.tenant_id) as session:
                    request = session.get(WorkRecord, (actor.tenant_id, request_id))
                    expires_at = request.payload["expires_at"] if request else ""
                subject = "Reminder: supplier relationship confirmation is awaiting review"
                body = (
                    "A previously sent supply-chain relationship confirmation is still awaiting "
                    "review. Please use this secure link before it expires:\n\n"
                    f"{portal_url}\n\nExpires at {expires_at}."
                )
            mailer.send(
                recipient,
                subject,
                body,
                hashlib.sha256(notification_id.encode()).hexdigest()[:24],
            )
        except Exception as error:
            _finish(store, actor.tenant_id, notification_id, payload, error)
        else:
            _finish(store, actor.tenant_id, notification_id, payload, None)
            delivered += 1
    return {"delivered": delivered, "attempted": attempted, "status": "processed"}
