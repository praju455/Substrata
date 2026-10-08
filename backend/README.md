# Backend

FastAPI implements the complete synthetic workflow. Entry point:
`substrata.app:app`; `create_app()` creates isolated test instances. Health has
no DB/network side effects. Workflow readiness requires the seeded database.

- `GET /health`, `/openapi.json`, `/docs` (default docs CDN needs internet).
- `GET /state`, `/graph`; `POST /mapper/run`, `/confirmations/simulate`.
- `POST /replay/start`, `/replay/pause`, `/replay/reset`.
- `POST /events/{id}/resolve`, `/scenarios/{id}/refresh`.
- `POST /approvals/{id}/decision`; `GET /audit/verify`, `/stream`.

OpenAPI describes request schemas. SSE is direct, persisted and resumable via
generation/cursor IDs. Use one local process, without multiple Uvicorn workers.
Five Alembic revisions create graph/provenance, ERP, agent/evaluation, workflow
and audit tables. SQLite enables WAL, foreign keys and busy timeout. Migrations
preserve data; seed/reset recreates synthetic business data atomically. Do not
initialize through `Base.metadata.create_all()`, which omits integrity triggers.

`graph.py` exposes GraphStore/NetworkX bounded traversal. `cascade.py` owns all
business formulas. `mapper.py` validates evidence extractions before writes;
`llm.py` calls Gemini first and Grok on provider failure. Explicit mock mode is offline. `runtime.py` freezes scenario inputs;
`governance.py` rejects stale, expired and duplicate approvals. `audit.py`
verifies the hash chain. All procurement execution is simulated.

Gemini/Grok adapters and failover are tested with intercepted HTTP, not live credentials.
See [LLM setup](../docs/LLM_SETUP.md) for keys and the missing-key 503 behavior.
SAP, broad retrieval, model training, authentication and production deployment
remain deferred. See the root README and docs/DECISIONS.md.
