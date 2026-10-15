"""Scoped graph changes and audit append share one transaction and tenant lock."""

import hashlib
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import Engine, select, text, update

from substrata.audit import digest, verify_chain
from substrata.platform.database import tenant_transaction
from substrata.platform.domain import GraphData, Provenance, Snapshot
from substrata.platform.models import AuditRecord, Document, GraphRevision, Organisation, WorkRecord
from substrata.seed import canonical


class GraphStore(Protocol):
    def snapshot(
        self, tenant_id: str, *, version: int | None = None, as_of: datetime | None = None
    ) -> Snapshot: ...


class Conflict(ValueError):
    """Optimistic graph version no longer matches the user's inputs."""


class PlatformStore:
    def __init__(self, engine: Engine):
        self.engine = engine
        if engine.dialect.name == "postgresql":
            with engine.connect() as connection:
                privileged = connection.execute(
                    text(
                        "SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname = current_user"
                    )
                ).scalar_one()
            if privileged:
                raise ValueError("Runtime database role must not be superuser or BYPASSRLS.")

    def provision(self, tenant_id: str, name: str, actor: str):
        if not name.strip() or not actor.strip():
            raise ValueError("Organisation name and authenticated actor are required.")
        with tenant_transaction(self.engine, tenant_id) as session:
            if session.get(Organisation, tenant_id):
                raise Conflict("Organisation already exists.")
            org = Organisation(
                tenant_id=tenant_id,
                name=name.strip(),
                version=0,
                audit_sequence=0,
                audit_head="0" * 64,
                policy={},
            )
            session.add(org)
            session.flush()
            self.append(session, org, "organisation.created", actor, {"name": org.name})

    @staticmethod
    def organisation(session, tenant_id):
        org = session.scalar(
            select(Organisation).where(Organisation.tenant_id == tenant_id).with_for_update()
        )
        if org is None:
            raise ValueError("Organisation is unavailable.")
        # An UPDATE also serialises SQLite writers before read/append operations.
        session.execute(
            update(Organisation)
            .where(Organisation.tenant_id == tenant_id)
            .values(version=Organisation.version)
        )
        session.refresh(org)
        return org

    @staticmethod
    def append(session, org, event_type, actor, payload):
        timestamp = datetime.now(UTC)
        record = {
            "sequence": org.audit_sequence + 1,
            "previous_hash": org.audit_head,
            "event_type": event_type,
            "actor": actor,
            "timestamp": timestamp.isoformat(),
            "payload": {"tenant_id": org.tenant_id, **payload},
        }
        sha = digest(record)
        session.add(
            AuditRecord(
                tenant_id=org.tenant_id, **{**record, "timestamp": timestamp}, payload_hash=sha
            )
        )
        org.audit_sequence += 1
        org.audit_head = sha
        return sha

    def snapshot(
        self, tenant_id: str, *, version: int | None = None, as_of: datetime | None = None
    ) -> Snapshot:
        if as_of is not None and (as_of.tzinfo is None or as_of.utcoffset() is None):
            raise ValueError("As-of dates must include a timezone.")
        with tenant_transaction(self.engine, tenant_id) as session:
            query = select(GraphRevision).where(GraphRevision.tenant_id == tenant_id)
            if version is not None:
                query = query.where(GraphRevision.version == version)
            if as_of is not None:
                query = query.where(GraphRevision.recorded_at <= as_of)
            row = session.scalar(query.order_by(GraphRevision.version.desc()).limit(1))
            if row is None:
                raise ValueError("No graph snapshot exists for this tenant and date/version.")
            if hashlib.sha256(canonical(row.payload).encode()).hexdigest() != row.sha256:
                raise ValueError("Graph snapshot integrity check failed.")
            return Snapshot(
                tenant_id=tenant_id,
                version=row.version,
                recorded_at=row.recorded_at,
                sha256=row.sha256,
                data=GraphData.model_validate(row.payload),
            )

    def save(
        self,
        tenant_id: str,
        data: GraphData,
        actor: str,
        *,
        expected_version: int,
        event_type: str = "graph.revised",
    ) -> Snapshot:
        with tenant_transaction(self.engine, tenant_id) as session:
            org = self.organisation(session, tenant_id)
            return self.save_in(
                session, org, data, actor, expected_version=expected_version, event_type=event_type
            )

    def save_in(
        self,
        session,
        org,
        data,
        actor,
        *,
        expected_version,
        event_type="graph.revised",
        confirmation_record_id=None,
    ):
        tenant_id = org.tenant_id
        data = GraphData.model_validate(data.model_dump())
        if org.version != expected_version:
            raise Conflict("Graph changed; refresh before saving.")
        previous = session.get(GraphRevision, (tenant_id, org.version))
        old_links = {link["id"]: link for link in previous.payload["links"]} if previous else {}
        for link in data.links:
            if link.status == "confirmed" and canonical(old_links.get(link.id)) != canonical(
                link.model_dump(mode="json")
            ):
                confirmation = (
                    session.get(WorkRecord, (tenant_id, confirmation_record_id))
                    if confirmation_record_id
                    else None
                )
                if (
                    confirmation is None
                    or confirmation.kind != "confirmation"
                    or confirmation.status != "confirmed"
                    or confirmation.payload["link_id"] != link.id
                ):
                    raise ValueError(
                        "New confirmations require a verified supplier response workflow."
                    )
            for citation in link.evidence:
                document = session.get(Document, (tenant_id, citation.document_id))
                if (
                    document is None
                    or document.text[citation.start : citation.end] != citation.passage
                ):
                    raise ValueError("Every citation must match a document in this tenant.")
        payload = data.model_dump(mode="json")
        sha = hashlib.sha256(canonical(payload).encode()).hexdigest()
        recorded_at = datetime.now(UTC)
        version = org.version + 1
        session.add(
            GraphRevision(
                tenant_id=tenant_id,
                version=version,
                recorded_at=recorded_at,
                sha256=sha,
                payload=payload,
            )
        )
        org.version = version
        self.append(session, org, event_type, actor, {"version": version, "sha256": sha})
        return Snapshot(
            tenant_id=tenant_id, version=version, recorded_at=recorded_at, sha256=sha, data=data
        )

    def add_document(
        self, tenant_id: str, document_id: str, text: str, provenance: Provenance, actor: str
    ):
        if not text.strip() or len(text.encode()) > 2_000_000:
            raise ValueError("Document text must be nonblank and at most 2 MB.")
        sha = hashlib.sha256(text.encode()).hexdigest()
        with tenant_transaction(self.engine, tenant_id) as session:
            org = self.organisation(session, tenant_id)
            previous = session.get(Document, (tenant_id, document_id))
            if previous is not None:
                if previous.sha256 != sha:
                    raise Conflict("Document ID is immutable; use a new ID for a changed document.")
                return sha
            session.add(
                Document(
                    tenant_id=tenant_id,
                    id=document_id,
                    text=text,
                    sha256=sha,
                    provenance=provenance.model_dump(mode="json"),
                )
            )
            self.append(session, org, "document.added", actor, {"id": document_id, "sha256": sha})
        return sha

    def audit(self, tenant_id: str, expected_head: str | None = None):
        with tenant_transaction(self.engine, tenant_id) as session:
            org = session.get(Organisation, tenant_id)
            if org is None:
                raise ValueError("Organisation is unavailable.")
            records = [
                {
                    "sequence": r.sequence,
                    "previous_hash": r.previous_hash,
                    "payload_hash": r.payload_hash,
                    "event_type": r.event_type,
                    "actor": r.actor,
                    "timestamp": r.timestamp.isoformat(),
                    "payload": r.payload,
                }
                for r in session.scalars(
                    select(AuditRecord)
                    .where(AuditRecord.tenant_id == tenant_id)
                    .order_by(AuditRecord.sequence)
                )
            ]
            return {
                "records": records,
                "verification": verify_chain(records, expected_head or org.audit_head),
            }
