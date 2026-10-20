"""Tenant-scoped workflow persistence; all changes have actor-attributed audit."""

import base64
import binascii
import json
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import and_, or_, select

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


def _cursor(created_at: datetime, id: str) -> str:
    raw = json.dumps([created_at.isoformat(), id], separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode_cursor(value: str) -> tuple[datetime, str]:
    try:
        raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
        created_at_value, id = json.loads(raw)
        created_at = datetime.fromisoformat(created_at_value)
        if (
            created_at.tzinfo is None
            or created_at.utcoffset() is None
            or not isinstance(id, str)
            or not 1 <= len(id) <= 256
        ):
            raise ValueError
        return created_at, id
    except (ValueError, TypeError, UnicodeDecodeError, binascii.Error, json.JSONDecodeError):
        raise ValueError("Record cursor is invalid.") from None


def record_page(store, tenant_id, *, kind=None, status=None, limit=50, cursor=None):
    """Stable keyset page scoped by tenant, kind and status."""
    limit = min(max(limit, 1), 200)
    with tenant_transaction(store.engine, tenant_id) as session:
        query = select(WorkRecord).where(WorkRecord.tenant_id == tenant_id)
        if kind:
            query = query.where(WorkRecord.kind == kind)
        if status:
            query = query.where(WorkRecord.status == status)
        if cursor:
            created_at, id = _decode_cursor(cursor)
            query = query.where(
                or_(
                    WorkRecord.created_at < created_at,
                    and_(WorkRecord.created_at == created_at, WorkRecord.id < id),
                )
            )
        rows = list(
            session.scalars(
                query.order_by(WorkRecord.created_at.desc(), WorkRecord.id.desc()).limit(limit + 1)
            )
        )
    page = rows[:limit]
    return {
        "items": [encode(row) for row in page],
        "next_cursor": _cursor(page[-1].created_at, page[-1].id)
        if len(rows) > limit and page
        else None,
    }


def require_record(session, tenant_id, id, kind=None):
    record = session.get(WorkRecord, (tenant_id, id))
    if record is None or (kind and record.kind != kind):
        raise ValueError("Workflow record is unavailable.")
    return record
