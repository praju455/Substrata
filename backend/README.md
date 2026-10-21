# Backend

FastAPI implements the complete synthetic workflow. Entry point:
`substrata.app:app`; `create_app()` creates isolated test instances. Health has
no DB/network side effects. Workflow readiness requires the seeded database.

- `GET /health`, `/openapi.json`, `/docs` (default docs CDN needs internet).
- `GET /state`, `/graph`; `POST /mapper/run`, `/confirmations/simulate`.
- `POST /replay/start`, `/replay/pause`, `/replay/reset`.
- `POST /events/{id}/resolve`, `/scenarios/{id}/refresh`.
- `POST /assistant/ask` for read-only graph/evidence/report questions with optional public-web evidence.
- `POST /approvals/{id}/decision`; `GET /audit/verify`, `/stream`.

OpenAPI describes request schemas. SSE is direct, persisted and resumable via
generation/cursor IDs. Use one local process, without multiple Uvicorn workers.
Five Alembic revisions create graph/provenance, ERP, agent/evaluation, workflow
and audit tables. SQLite enables WAL, foreign keys and busy timeout. Migrations
preserve data; seed/reset recreates synthetic business data atomically. Do not
initialize through `Base.metadata.create_all()`, which omits integrity triggers.

`graph.py` exposes GraphStore/NetworkX bounded traversal. `cascade.py` owns all
business formulas. `mapper.py` validates evidence extractions before writes;
`llm.py` calls Gemini first and Groq on provider failure. Explicit mock mode is offline. `runtime.py` freezes scenario inputs;
`governance.py` rejects stale, expired and duplicate approvals. `audit.py`
verifies the hash chain. All procurement execution is simulated.

`platform/assistant.py` uses LangGraph to route retrieval, optional Tavily search,
generation and validation. LangChain assembles only the retrieved context. The
assistant returns cited `known`, `inferred` and `unknown` claims and cannot confirm
relationships, perform impact arithmetic, approve actions or write to SAP. It
queries graph facts and saved reports directly, so this flow requires no uploaded
document or vector database. Google Gen AI SDK and Groq are optional live adapters;
the default mock is deterministic and offline.

Gemini/Groq adapters and failover are tested with intercepted HTTP, not live credentials.
See [LLM setup](../docs/LLM_SETUP.md) for keys and the missing-key 503 behavior.
SAP connectivity, custom model training and production deployment remain deferred.
See the root README and docs/DECISIONS.md.
