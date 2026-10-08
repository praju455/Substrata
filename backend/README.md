# Backend

The `substrata` Python package now provides a minimal FastAPI app:

- `GET /health`: typed process-liveness response labelled `synthetic`.
- `GET /openapi.json`: generated API contract.
- `GET /docs`: default interactive API documentation (CDN assets need internet).

Use the verified commands in the root [README](../README.md#getting-started).
`create_app()` constructs an independent app for tests; `substrata.app:app` is
the Uvicorn entry point. Health does not assert database or scenario readiness.

M1.1 adds `database.py`: a file-backed SQLAlchemy engine with SQLite WAL,
foreign-key enforcement, a five-second busy timeout, typed model metadata and
a transaction helper that commits on success or rolls back on failure.
No database is opened or migrated when the app is imported or started.

Run `python scripts/dev.py migrate` from the repository root to create/upgrade
`data/substrata.sqlite3`. The current Alembic baseline creates only schema
history (`alembic_version`). Repeated upgrades preserve existing records;
this command does not seed or reset data. Domain schema changes will use new,
checked-in revisions in `substrata/migrations/versions`.

Graph/ERP tables, deterministic graph/runway calculations, orchestration,
approvals and audit remain planned. **[Design]** See the
[build checklist](../docs/BUILD_PLAN.md).
