"""Append-only canonical hash chain; original truth and external anchoring are separate."""

import hashlib
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from substrata.seed import canonical
from substrata.workflow_models import AuditEvent

GENESIS = "0" * 64


def audit_record(row: AuditEvent) -> dict:
    return {
        "sequence": row.sequence,
        "previous_hash": row.previous_hash,
        "payload_hash": row.payload_hash,
        "event_type": row.event_type,
        "actor": row.actor,
        "timestamp": row.timestamp.isoformat(),
        "payload": row.payload,
    }


def digest(record: dict) -> str:
    return hashlib.sha256(
        canonical({k: v for k, v in record.items() if k != "payload_hash"}).encode()
    ).hexdigest()


def verify_chain(records: list[dict], expected_head: str | None = None) -> dict:
    previous = GENESIS
    for sequence, record in enumerate(records, start=1):
        if (
            record["sequence"] != sequence
            or record["previous_hash"] != previous
            or digest(record) != record["payload_hash"]
        ):
            return {
                "valid": False,
                "count": len(records),
                "head": previous,
                "error_sequence": sequence,
            }
        previous = record["payload_hash"]
    valid = expected_head is None or previous == expected_head
    return {
        "valid": valid,
        "count": len(records),
        "head": previous,
        "error_sequence": None if valid else len(records) + 1,
    }


def records_in(session: Session) -> list[dict]:
    return [
        audit_record(row)
        for row in session.scalars(select(AuditEvent).order_by(AuditEvent.sequence))
    ]


def append_audit(
    session: Session, event_type: str, actor: str, payload: dict, timestamp: datetime | None = None
) -> AuditEvent:
    records = records_in(session)
    verification = verify_chain(records)
    if not verification["valid"]:
        raise ValueError("Audit chain verification failed; further decisions are blocked.")
    timestamp = (timestamp or datetime.now(UTC)).astimezone(UTC)
    record = {
        "sequence": len(records) + 1,
        "previous_hash": verification["head"],
        "event_type": event_type,
        "actor": actor,
        "timestamp": timestamp.isoformat(),
        "payload": payload,
    }
    row = AuditEvent(**{**record, "timestamp": timestamp, "payload_hash": digest(record)})
    session.add(row)
    session.flush()
    return row
