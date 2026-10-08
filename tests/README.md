# Tests

Run `python scripts/dev.py test` and `python scripts/dev.py lint` from the root.
Tests use temporary SQLite files, synthetic fixtures and offline mocks.

- API health/OpenAPI; launcher ports, precedence and static-build API URL.
- WAL, foreign keys, transactions, concurrent readers and migrations.
- Typed graph payloads, versioned endpoints, bounds, units, UTC and provenance.
- ERP, deterministic seed, truth isolation and failed-reset rollback.
- Bounded paths, cycles, shared parents, arrival eligibility, 18/90/72 example,
  multiple-path scores, zero demand and missing inputs.
- Mapper evidence validation, thresholds, idempotency, invalid-output logging,
  simulated confirmations and Gemini/Grok transport, failover/recovery, missing-key
  503, invalid/oversized response and credential-redaction contracts.
- Policy, named approval, stale/expired/duplicate requests and audit tampering.
- Full API/SSE/reset loop, analyst escalation, refreshed snapshots, CORS,
  pause/resume and ten identical semantic hashes across seeded replays.

Browser checks are recorded separately in docs/BUILD_PLAN.md. Frozen fixture
results are not a held-out benchmark or evidence of real-world accuracy.
