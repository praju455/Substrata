"""Signed, expiring, single-use supplier portal responses become labelled revisions."""

import hashlib
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

import jwt
from cryptography.fernet import Fernet
from pydantic import Field

from substrata.platform.database import tenant_transaction
from substrata.platform.domain import Contract, GraphData
from substrata.platform.records import add, encode, require_record
from substrata.platform.store import Conflict
from substrata.seed import canonical


class ConfirmationInput(Contract):
    link_id: str
    recipient_email: str | None = Field(default=None, max_length=256)
    expiry_hours: int = Field(default=72, ge=1, le=168)


class SupplierReply(Contract):
    token: str = Field(min_length=1, max_length=16384)
    decision: Literal["confirmed", "rejected"]
    responder: str = Field(min_length=1, max_length=96)
    reason: str = Field(min_length=1, max_length=2000)


class PortalSigner:
    def __init__(self, key: str):
        if len(key.encode()) < 32:
            raise ValueError("Confirmation signing key must be at least 32 bytes.")
        self.key = key

    def sign(self, tenant_id, id, expiry):
        now = datetime.now(UTC)
        return jwt.encode(
            {
                "iss": "substrata-confirmations",
                "aud": "supplier-portal",
                "tenant_id": tenant_id,
                "jti": id,
                "iat": now,
                "nbf": now,
                "exp": expiry,
            },
            self.key,
            algorithm="HS256",
        )

    def verify(self, token):
        try:
            return jwt.decode(
                token,
                self.key,
                algorithms=["HS256"],
                issuer="substrata-confirmations",
                audience="supplier-portal",
                options={"require": ["iss", "aud", "tenant_id", "jti", "iat", "nbf", "exp"]},
            )
        except jwt.PyJWTError:
            raise ValueError("Supplier portal token is invalid or expired.") from None


def configured_signer():
    keyfile = os.environ.get("SUBSTRATA_CONFIRMATION_KEY_FILE")
    if not keyfile:
        raise ValueError("Configure a permission-restricted supplier confirmation signing key.")
    return PortalSigner(Path(keyfile).read_text(encoding="utf-8").strip())


def privacy_cipher():
    path = os.environ.get("SUBSTRATA_PII_KEY_FILE")
    if not path:
        raise ValueError("A restricted PII encryption key file is required for outbound contact.")
    return Fernet(Path(path).read_bytes().strip())


def create_request(store, actor, body: ConfirmationInput, *, signer=None):
    actor.require("analyst")
    signer = signer or configured_signer()
    snapshot = store.snapshot(actor.tenant_id)
    link = next((e for e in snapshot.data.links if e.id == body.link_id), None)
    if link is None or link.status not in {"declared", "inferred"}:
        raise ValueError("Only declared/inferred tenant links can request confirmation.")
    encrypted_recipient = None
    development = os.environ.get("SUBSTRATA_ENV", "development") == "development"
    if not development and not body.recipient_email:
        raise ValueError("Production confirmation requires a supplier recipient and delivery.")
    if body.recipient_email:
        if (
            "@" not in body.recipient_email
            or "\n" in body.recipient_email
            or "\r" in body.recipient_email
        ):
            raise ValueError("Supplier email address is invalid.")
        encrypted_recipient = privacy_cipher().encrypt(body.recipient_email.encode()).decode()
    expires = datetime.now(UTC) + timedelta(hours=body.expiry_hours)
    with tenant_transaction(store.engine, actor.tenant_id) as session:
        org = store.organisation(session, actor.tenant_id)
        if org.version != snapshot.version:
            raise Conflict("Graph changed; refresh the confirmation request.")
        record = add(
            session,
            actor.tenant_id,
            "confirmation",
            "pending",
            {
                "link_id": link.id,
                "link_sha256": hashlib.sha256(
                    canonical(link.model_dump(mode="json")).encode()
                ).hexdigest(),
                "graph_version": snapshot.version,
                "expires_at": expires.isoformat(),
                "recipient_ciphertext": encrypted_recipient,
                "remind_after": (datetime.now(UTC) + timedelta(hours=24)).isoformat(),
                "reminders_sent": 0,
                "features": {
                    "evidence_count": len(link.evidence),
                    "supplier_source": int(link.provenance.kind == "supplier"),
                    "explicit_endpoints": 1,
                    "rule_score": link.confidence,
                },
            },
        )
        token = signer.sign(actor.tenant_id, record.id, expires)
        portal = os.environ.get("SUBSTRATA_PORTAL_URL", "http://127.0.0.1:3000/confirm/")
        if os.environ.get(
            "SUBSTRATA_ENV", "development"
        ) != "development" and not portal.startswith("https://"):
            raise ValueError("Production supplier portal requires HTTPS.")
        url = portal + "#token=" + token
        add(
            session,
            actor.tenant_id,
            "notification",
            "pending",
            {
                "type": "supplier_confirmation",
                "request_id": record.id,
                "portal_ciphertext": privacy_cipher().encrypt(url.encode()).decode()
                if encrypted_recipient
                else None,
                "recipient_ciphertext": encrypted_recipient,
                "channel": "email" if encrypted_recipient else "portal",
            },
        )
        store.append(
            session,
            org,
            "confirmation.requested",
            actor.subject,
            {
                "id": record.id,
                "link_id": link.id,
                "expires_at": expires.isoformat(),
                "outbound_mode": "development preview"
                if os.environ.get("SUBSTRATA_ENV", "development") == "development"
                else "configured delivery",
            },
        )
        return {
            "request": encode(record),
            "portal_url": url if development else None,
            "delivery_queued": bool(encrypted_recipient),
        }


def describe_request(store, token, *, signer=None):
    claims = (signer or configured_signer()).verify(token)
    with tenant_transaction(store.engine, claims["tenant_id"]) as session:
        record = require_record(session, claims["tenant_id"], claims["jti"], "confirmation")
        snapshot = store.snapshot(claims["tenant_id"])
        link = next((e for e in snapshot.data.links if e.id == record.payload["link_id"]), None)
        if link is None:
            raise ValueError("Relationship is unavailable.")
        names = {e.id: e.name for e in snapshot.data.entities}
        return {
            "request_id": record.id,
            "status": record.status,
            "source": names[link.source],
            "target": names[link.target],
            "type": link.type,
            "expires_at": record.payload["expires_at"],
            "passages": [c.passage for c in link.evidence],
        }


def reply(store, body: SupplierReply, *, signer=None):
    claims = (signer or configured_signer()).verify(body.token)
    tenant_id = claims["tenant_id"]
    snapshot = store.snapshot(tenant_id)
    with tenant_transaction(store.engine, tenant_id) as session:
        org = store.organisation(session, tenant_id)
        request = require_record(session, tenant_id, claims["jti"], "confirmation")
        if request.status != "pending":
            raise Conflict("Supplier response token has already been used.")
        if datetime.now(UTC) >= datetime.fromisoformat(request.payload["expires_at"]):
            raise ValueError("Supplier request has expired.")
        link = next((e for e in snapshot.data.links if e.id == request.payload["link_id"]), None)
        if (
            link is None
            or hashlib.sha256(canonical(link.model_dump(mode="json")).encode()).hexdigest()
            != request.payload["link_sha256"]
        ):
            raise Conflict("Relationship changed; request a new confirmation.")
        if not body.responder.strip() or not body.reason.strip():
            raise ValueError("Responder and rationale must be nonblank.")
        request.status = body.decision
        request.payload = {
            **request.payload,
            "response": {
                "decision": body.decision,
                "responder": body.responder,
                "reason": body.reason,
                "at": datetime.now(UTC).isoformat(),
            },
        }
        session.flush()
        links = [
            e.model_copy(update={"status": body.decision}) if e.id == link.id else e
            for e in snapshot.data.links
        ]
        data = GraphData.model_validate(
            snapshot.data.model_copy(update={"links": links}).model_dump()
        )
        frozen = store.save_in(
            session,
            org,
            data,
            "supplier:" + body.responder,
            expected_version=snapshot.version,
            confirmation_record_id=request.id,
            event_type="supplier.link." + body.decision,
        )
        add(
            session,
            tenant_id,
            "training_label",
            "labelled",
            {
                "link_id": link.id,
                "label": int(body.decision == "confirmed"),
                "group_id": link.source,
                "synthetic": link.provenance.kind == "synthetic",
                "features": request.payload["features"],
                "provenance": {
                    "kind": "supplier",
                    "request_id": request.id,
                    "recorded_at": datetime.now(UTC).isoformat(),
                },
                "graph_version": frozen.version,
            },
        )
        return {"decision": body.decision, "graph_version": frozen.version}
