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
`data/substrata.sqlite3`. M1.2 adds five graph/provenance tables after the baseline:
`graph_nodes`, `graph_edges`, `source_snapshots`, `evidence_records` and
`edge_evidence`. Repeated upgrades preserve existing records; this command does
not seed or reset data. Schema changes use new, checked-in revisions in
`substrata/migrations/versions`; do not use `Base.metadata.create_all()` to
initialize the application because it omits migration-owned triggers.

`models.py` provides typed ORM records and UTC timestamp handling;
`graph_types.py` validates type-specific node attributes. Versioned endpoint
foreign keys prevent cross-version or wrongly typed links. Inferred edges
require evidence; migration-owned triggers retain a supporting primary citation
and block confirmation updates until the human workflow exists. See the
[implemented data model](../docs/DATA_MODEL.md#implemented-graph-and-provenance-schema-m12)
for the constraints and remaining validation boundaries.

ERP tables, deterministic graph/runway calculations, orchestration,
approvals and audit remain planned. **[Design]** See the
[build checklist](../docs/BUILD_PLAN.md).
