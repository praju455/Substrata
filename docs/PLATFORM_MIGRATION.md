# Platform migration

The approved target is the ten-part platform brief audited on 14 October 2026.
The existing synthetic replay remains available while platform capabilities
arrive behind `SUBSTRATA_PLATFORM_ENABLED`. Completion of a foundation checkpoint
does not establish pilot readiness or general availability.

## Implemented foundation

`substrata.platform` has a separate portable Alembic history. Its organisation,
graph revision, document and audit keys are tenant-scoped. SQLite supports offline
tests; PostgreSQL/psycopg is the production database path. PostgreSQL tables force
row-level security using transaction-local `substrata.tenant_id`; runtime roles
must be neither superusers nor BYPASSRLS roles. Migration credentials are separate.

Graph revisions are complete immutable snapshots. A revision is recorded at commit
time; `as_of` selects the most recent recorded revision at or before that timestamp.
Link business validity is separate from recording time. Optimistic version checks
reject stale changes. Graph writes and their audit event commit atomically.
Historical status changes therefore do not rewrite earlier graph states.

Entities cover suppliers, sites, materials, products, plants and regions, alongside
BOM, inventory and purchase-order contracts. Every numerical business measurement
requires a unit and provenance. Inferred links require exact document passages;
citations must resolve to an immutable document belonging to the same tenant.
Audit exports include the chain head for independent anchoring and verification.

## Delivery sequence and acceptance

1. Tenant context, portable migrations, immutable graph/provenance and atomic audit.
2. Authenticated API, OIDC/RBAC, tenant policy and feature-flagged product access.
3. Imports/connectors, entity resolution and data-quality/onboarding workflows.
4. Multi-industry scenarios, deterministic cascade, uncertainty and graph exploration.
5. Retrieval/extraction, signed confirmations, scoring training and evaluation.
6. Feeds, durable agents, approval notifications, exports, MCP/A2A and operations.

The final review must map every requirement to executable tests, runtime behavior
or a documented external configuration gate. Real supplier contact is disabled in
development, execution defaults to dry-run, and no SAP affiliation is claimed.
No claims of production readiness follow merely from passing offline tests.
