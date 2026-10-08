# Backend

The `substrata` Python package now provides a minimal FastAPI app:

- `GET /health`: typed process-liveness response labelled `synthetic`.
- `GET /openapi.json`: generated API contract.
- `GET /docs`: default interactive API documentation (CDN assets need internet).

Use the verified commands in the root [README](../README.md#getting-started-backend-scaffold).
`create_app()` constructs an independent app for tests; `substrata.app:app` is
the Uvicorn entry point. Health does not assert database or scenario readiness.

Persistence, deterministic graph/runway calculations, orchestration, approvals
and audit remain planned. **[Design]** See the [build checklist](../docs/BUILD_PLAN.md).
