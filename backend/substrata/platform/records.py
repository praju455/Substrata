"""Tenant-scoped workflow persistence; all changes have actor-attributed audit."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select

from substrata.platform.database import tenant_transaction
from substrata.platform.models import WorkRecord


def add(session, tenant_id, kind, status, payload, id=None):
    record = WorkRecord(
        tenant_id=tenant_id,
        id=id or str(uuid4()),
        kind=kind,
        status=status,
        payload=payload,
        created_at=datetime.now(UTC),
    )
    session.add(record)
    return record


def encode(record):
    return {
        "id": record.id,
        "kind": record.kind,
        "status": record.status,
        "created_at": record.created_at.isoformat(),
        "payload": {
            key: value
            for key, value in record.payload.items()
            if key
            not in {"recipient_ciphertext", "portal_url", "portal_ciphertext", "token", "claim_id"}
        },
    }


def list_records(store, tenant_id, *, kind=None, status=None, limit=200):
    with tenant_transaction(store.engine, tenant_id) as session:
        query = select(WorkRecord).where(WorkRecord.tenant_id == tenant_id)
        if kind:
            query = query.where(WorkRecord.kind == kind)
        if status:
            query = query.where(WorkRecord.status == status)
        return [
            encode(row)
            for row in session.scalars(
                query.order_by(WorkRecord.created_at.desc()).limit(min(limit, 500))
            )
        ]


def require_record(session, tenant_id, id, kind=None):
    record = session.get(WorkRecord, (tenant_id, id))
    if record is None or (kind and record.kind != kind):
        raise ValueError("Workflow record is unavailable.")
    return record
