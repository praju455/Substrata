"""Document chunks and exact citations are tenant-scoped and treated as data."""

import hashlib
from datetime import UTC, datetime

from sqlalchemy import select, text

from substrata.platform.budgets import reserve, settle
from substrata.platform.database import tenant_transaction
from substrata.platform.domain import GraphData, Link, Provenance
from substrata.platform.models import Document, DocumentChunk
from substrata.platform.providers import configured_embedder, configured_extractor
from substrata.platform.records import add, encode
from substrata.platform.store import Conflict
from substrata.seed import canonical


def index_documents(store, actor, embedder=None):
    actor.require("analyst")
    embedder = embedder or configured_embedder()
    with tenant_transaction(store.engine, actor.tenant_id) as session:
        documents = [
            (d.id, d.text)
            for d in session.scalars(select(Document).where(Document.tenant_id == actor.tenant_id))
        ]
        known = {
            (c.document_id, c.position)
            for c in session.scalars(
                select(DocumentChunk).where(
                    DocumentChunk.tenant_id == actor.tenant_id,
                    DocumentChunk.embedding_model == embedder.model,
                )
            )
        }
    count = 0
    for document_id, content in documents:
        chunks = [
            (position, start, content[start : start + 1800])
            for position, start in enumerate(range(0, len(content), 1500))
            if (document_id, position) not in known
        ]
        if not chunks:
            continue
        texts = [value for _, _, value in chunks]
        reservation = (
            reserve(store, actor, embedder.maximum_cost(texts), "document.embeddings")
            if hasattr(embedder, "maximum_cost")
            else None
        )
        try:
            embeddings = embedder.embed(texts)
        finally:
            if reservation:
                settle(
                    store,
                    actor,
                    reservation,
                    getattr(embedder, "telemetry", {}).get("estimated_cost_usd"),
                )
        if len(embeddings) != len(chunks):
            raise ValueError("Embedding provider returned the wrong vector count.")
        with tenant_transaction(store.engine, actor.tenant_id) as session:
            org = store.organisation(session, actor.tenant_id)
            for (position, start, passage), embedding in zip(chunks, embeddings, strict=True):
                existing = session.get(
                    DocumentChunk, (actor.tenant_id, document_id, position, embedder.model)
                )
                if existing is not None:
                    continue
                session.add(
                    DocumentChunk(
                        tenant_id=actor.tenant_id,
                        document_id=document_id,
                        position=position,
                        start=start,
                        end=start + len(passage),
                        text=passage,
                        embedding=embedding,
                        embedding_model=embedder.model,
                    )
                )
                count += 1
            store.append(
                session,
                org,
                "documents.indexed",
                actor.subject,
                {"document_id": document_id, "embedding_model": embedder.model},
            )
    return {"indexed_chunks": count, "embedding_model": embedder.model}


def retrieve(store, tenant_id, query, *, limit=8, embedder=None, actor=None):
    if not query.strip() or len(query) > 2000 or not 1 <= limit <= 20:
        raise ValueError("Query must be nonblank and bounded; limit must be 1–20.")
    embedder = embedder or configured_embedder()
    reservation = None
    if hasattr(embedder, "maximum_cost"):
        if actor is None or actor.tenant_id != tenant_id:
            raise ValueError("Live semantic retrieval requires authenticated tenant context.")
        reservation = reserve(store, actor, embedder.maximum_cost([query]), "query.embedding")
    try:
        vector = embedder.embed([query])[0]
    finally:
        if reservation:
            settle(
                store,
                actor,
                reservation,
                getattr(embedder, "telemetry", {}).get("estimated_cost_usd"),
            )
    with tenant_transaction(store.engine, tenant_id) as session:
        if store.engine.dialect.name == "postgresql":
            rows = session.execute(
                text("""SELECT document_id, start, "end", text,
                       1 - (embedding <=> CAST(:vector AS vector)) AS score
                       FROM document_chunks WHERE tenant_id=:tenant AND embedding_model=:model
                       ORDER BY embedding <=> CAST(:vector AS vector), document_id, position
                       LIMIT :limit"""),
                {
                    "vector": canonical(vector),
                    "tenant": tenant_id,
                    "model": embedder.model,
                    "limit": limit,
                },
            )
            return [dict(row._mapping) for row in rows]
        chunks = list(
            session.scalars(
                select(DocumentChunk).where(
                    DocumentChunk.tenant_id == tenant_id,
                    DocumentChunk.embedding_model == embedder.model,
                )
            )
        )
        ranked = [
            {
                "document_id": chunk.document_id,
                "start": chunk.start,
                "end": chunk.end,
                "text": chunk.text,
                "score": sum(a * b for a, b in zip(vector, chunk.embedding, strict=True)),
            }
            for chunk in chunks
        ]
        return sorted(ranked, key=lambda r: (-r["score"], r["document_id"], r["start"]))[:limit]


def discover(store, actor, query, *, extractor=None):
    actor.require("analyst")
    index_documents(store, actor)
    passages = retrieve(store, actor.tenant_id, query, actor=actor)
    snapshot = store.snapshot(actor.tenant_id)
    extractor = extractor or configured_extractor()
    entities = [
        {"id": e.id, "name": e.name, "kind": e.kind}
        for e in snapshot.data.entities
        if any(e.name in passage["text"] for passage in passages)
    ]
    if len(entities) > 200:
        raise ValueError("Too many candidate entities; narrow the retrieval query.")
    reservation = (
        reserve(store, actor, extractor.maximum_cost(passages, entities), "mapper.extraction")
        if hasattr(extractor, "maximum_cost")
        else None
    )
    telemetry = {}
    try:
        extraction, telemetry = extractor.extract(passages, entities)
    except Exception as exc:
        with tenant_transaction(store.engine, actor.tenant_id) as session:
            org = store.organisation(session, actor.tenant_id)
            run = add(
                session,
                actor.tenant_id,
                "agent_run",
                "failed",
                {
                    "agent": "Mapper",
                    "provider": extractor.provider,
                    "model": extractor.model,
                    "error_type": type(exc).__name__,
                    "graph_version": snapshot.version,
                },
            )
            store.append(
                session,
                org,
                "mapper.failed",
                actor.subject,
                {"id": run.id, "error_type": type(exc).__name__},
            )
        raise ValueError("Mapper extraction failed; no graph changes were applied.") from None
    finally:
        if reservation:
            settle(store, actor, reservation, telemetry.get("estimated_cost_usd"))
    with tenant_transaction(store.engine, actor.tenant_id) as session:
        org = store.organisation(session, actor.tenant_id)
        if org.version != snapshot.version:
            raise Conflict("Graph changed during extraction; rerun discovery.")
        links = {link.id: link for link in snapshot.data.links}
        nodes = {entity.id: entity for entity in snapshot.data.entities}
        inferred = []
        for relation in extraction.relations:
            citation = relation.citation
            document = session.get(Document, (actor.tenant_id, citation.document_id))
            if document is None or document.text[citation.start : citation.end] != citation.passage:
                raise ValueError("Extraction passage does not match a tenant document.")
            if (
                relation.source not in nodes
                or relation.target not in nodes
                or relation.source == relation.target
            ):
                raise ValueError("Extraction endpoints must exist in the tenant graph.")
            if (
                nodes[relation.source].name not in citation.passage
                or nodes[relation.target].name not in citation.passage
            ):
                raise ValueError("Passage must identify both extracted entities.")
            id = (
                "inferred-"
                + hashlib.sha256(
                    canonical([relation.source, relation.target, relation.type]).encode()
                ).hexdigest()[:32]
            )
            if id in links:
                continue
            provenance = Provenance(
                uri=f"document://{citation.document_id}",
                observed_at=datetime.now(UTC),
                kind=document.provenance["kind"],
                note=(
                    f"Uncalibrated rule-supported proposal; provider={extractor.provider}; "
                    f"prompt={telemetry['prompt_version']}"
                ),
            )
            from substrata.platform.scoring import score

            scoring = score(
                store,
                actor.tenant_id,
                {
                    "evidence_count": 1,
                    "supplier_source": int(document.provenance["kind"] == "supplier"),
                    "explicit_endpoints": 1,
                    "rule_score": 0.65,
                },
            )
            provenance = provenance.model_copy(
                update={
                    "note": provenance.note
                    + f"; scorer={scoring['model_version']}; calibrated={scoring['calibrated']}"
                }
            )
            links[id] = Link(
                id=id,
                source=relation.source,
                target=relation.target,
                type=relation.type,
                confidence=scoring["score"],
                status="inferred",
                evidence=[citation],
                provenance=provenance,
                valid_from=datetime.now(UTC),
            )
            inferred.append(id)
        data = snapshot.data.model_copy(update={"links": list(links.values())})
        # Validate endpoint direction and references after adding extracted claims.
        data = GraphData.model_validate(data.model_dump())
        if inferred:
            store.save_in(
                session,
                org,
                data,
                actor.subject,
                expected_version=snapshot.version,
                event_type="evidence.links.proposed",
            )
        run = add(
            session,
            actor.tenant_id,
            "agent_run",
            "completed",
            {
                "agent": "Mapper",
                "inferred_ids": inferred,
                "telemetry": telemetry,
                "extraction": extraction.model_dump(mode="json"),
                "graph_version": org.version,
            },
        )
        store.append(
            session,
            org,
            "mapper.completed",
            actor.subject,
            {"id": run.id, "inferred_ids": inferred, "telemetry": telemetry},
        )
        return encode(run)
