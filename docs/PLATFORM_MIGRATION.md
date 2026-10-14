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

The small link scorer trains gradient-boosted trees on supplier confirm/reject
features, calibrates on a separate supplier-group split and reports held-out
precision, recall, average precision, Brier score, calibration points and errors.
At least 50 labels across 10 supplier groups are required, with both classes in
each split. Models have feature/library/data/artifact versions and hash-verified
registry files. Explicit activation requires evaluation gates; synthetic-trained
models cannot be activated in production. No LLM fine-tuning is performed.
Use `python -m scripts.train_scorer --labels labels.json --output new-model-dir`.
Synthetic training tests establish the pipeline, not customer accuracy.

Supplier confirmations use signed, expiring, single-use portal tokens. Tokens live
in the URL fragment and are posted in the body, not server request URLs. They bind
to one tenant/request and reject changed link inputs. Confirm/reject replies create
immutable graph revisions and supplier-provenance training labels. Direct analyst
graph writes cannot introduce or modify confirmed relationships without a verified
response workflow. Inbox payloads redact portal credentials/contact ciphertext.
Supplier recipient addresses and portal links are Fernet-encrypted. Development
returns a preview portal link and disables supplier email delivery; production may
deliver queued confirmations using an explicitly configured SMTP-over-TLS transport.

Documents are immutable and indexed into offset-preserving chunks. PostgreSQL uses
pgvector cosine retrieval with tenant policies; SQLite uses the same bounded vector
contracts offline. The default hashing-word baseline is explicitly lexical, not
semantic. Configure a 384-dimensional OpenAI-compatible embedding provider for
semantic retrieval. Embedding model versions coexist instead of silently replacing
older vectors. Extractors support OpenAI, Anthropic, local compatible HTTP and an
explicit offline mock. Strict JSON schema, retries/timeouts and exact document
spans prevent unsupported writes; evidence is data, never executable instructions.

Live inference requires sourced provider input/output prices in
`USD/million_tokens` and a sourced tenant `llm_daily_budget` in USD. Daily cost
reservations serialize across requests and conservatively retain charges when
upstream usage is unknown. Logs carry provider/model/prompt, token usage, latency
and estimated cost without credentials. Live provider access remains configuration
dependent; intercepted-response tests do not establish live availability.

Provider contracts follow [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs),
[OpenAI embeddings](https://developers.openai.com/api/reference/resources/embeddings/methods/create)
and [Anthropic structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs).

The `/platform/` frontend includes organisation onboarding, data-quality counts,
CSV/Excel mapping, graph status/search/history, deterministic scenario/runway,
policy setup, approval/rejection, notifications and audit/CSV exports. SSO uses
authorization code with PKCE; access tokens remain in component memory. Configure
an OIDC public client, audience mapping, tenant/role claims and exact redirect URI.
SAML login is brokered by that identity provider. Development token entry is only
offered when the server explicitly identifies development mode.
Graph positioning derives dependency depth from edges, independent of ID naming.
Browser verification used an isolated synthetic tenant: sign-in, organisation
creation, pharma seed loading and the 17.54/120/102.46-day runway rendered correctly.
At the scorer checkpoint the Python suite passed 181 tests. The event/job/agent
checkpoint passed 189 tests and the current operations checkpoint adds readiness
and observability checks. Static export and frontend type/lint checks passed. This
does not verify a live customer IdP or production PostgreSQL deployment.

REST ingestion accepts typed graphs with tenant-scoped idempotency keys; webhooks
add an HMAC signature over exact request bytes plus authenticated machine identity.
OData adapters perform GET only, bound response/page/row budgets, refuse redirects
and keep pagination on the configured origin. Configuration and credential files
are server-side and scoped to a tenant. SAP Business Network/Ariba remains an
explicit adapter stub as requested; it does not substitute mock data for real data.

Run the development OData mock with
`python -m uvicorn scripts.mock_sap:app --host 127.0.0.1 --port 8521`.
Example connector config (supplied through `SUBSTRATA_CONNECTORS_FILE`):

```json
[{"name":"mock","tenant_id":"demo","base_url":"http://127.0.0.1:8521/odata/",
  "resources":{"vendors":"entities"},"synthetic":true}]
```

`/platform/connectors/{name}/read/{resource}` returns rows for explicit column/unit
mapping. Actual S/4HANA resource paths, credentials and mappings are supplied per
customer system; access and real-system semantics have not been validated locally.
Mock responses remain visibly synthetic. No SAP affiliation is claimed.

Tenant policies specify sourced currency/spend/automatic-approval thresholds,
approval SLA, roles and requester/approver separation. Assessments persist their
input snapshots. Mitigation drafts use sourced quotes rather than the legacy
fixed-price templates. Decisions freeze policy/graph hashes, require authenticated
authority and reasons, support delegation and create portal notification records.
Stale/expired inputs block approval. Execution is idempotent and dry-run by default;
real SAP adapters additionally require an explicit feature flag, human approval
and a non-development environment. No production adapter is assumed configured.

CSV/XLSX ingestion supports a mapping preview, validated staged rows, duplicate
identities, schema fingerprint checks, import history, idempotent apply and safe
rollback. Uploads are bounded to 3 MB, 10000 rows and 100 columns; expanded Excel
archives are bounded to 20 MB. Ambiguous normalised-name matches pause in review.
Rollback creates a new graph revision and refuses to overwrite subsequent work.
The source URI, observation time, units and source kind are supplied explicitly.

The platform cascade reuses the tested runway arithmetic and bounded traversal,
adds elapsed-stock handling, eligible PO arrivals, shared ancestors, supply-share
concentration, affected products and sourced gross revenue at risk. It reports
exposure ranges when dependencies are inferred. Evidence-support bounds use
Fréchet/union bounds without an independence assumption; these are not calibrated
disruption probabilities. Missing inventory is incomplete rather than unaffected.
Tests include multi-industry golden results and generated stock monotonicity.
`POST /platform/seeds` supplies clearly synthetic automotive, pharma and food
fixtures only in development. `/platform/scenarios/assess` accepts an explicit
source, date, graph version and bounded traversal depth.
Run `python -m scripts.platform_graph_load` for repeatable concurrent traversal
measurements on a generated binary tree. The harness reports query latency and
throughput, labels all input as synthetic, and has no production performance
threshold; pilot sizing still needs representative customer-shaped graphs.

Event subscriptions and user-submitted events are tenant-scoped, deduplicated and
audited. RSS/Atom inputs are bounded, HTTPS-only and restricted to an operator
host allowlist; each configured feed carries an explicit licensing note. Heuristic
severity and entity-match scores are labelled assumptions, while ambiguous matches
wait for an authenticated analyst. Alert acknowledgement and event resolution are
audited. A GDELT DOC ArticleList adapter consumes its RSS output with bounded query
windows and result counts; configure `api.gdeltproject.org` in the host allowlist
and provide an operator-reviewed attribution/license note. See the [GDELT DOC API
description](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/). An NWS active
weather-alert adapter accepts a two-letter U.S. area code, validates the official
API response and requires a configured identifying User-Agent. Configure
`api.weather.gov` in the host allowlist and review [NWS API guidance](https://www.weather.gov/documentation/services-web-api)
before production polling. This feed is U.S.-only. Port/congestion and
sanctions/export-control registries still need source-specific parsers; licensed
providers that expose bounded event JSON can be connected through the field-mapped
`json_api` adapter. It does not perform legal screening, download bulk sanctions
lists, or bundle a port/sanctions provider. No source key or licensing rights are
bundled.

Example tenant-scoped feed configuration:

```json
[
  {
    "tenant_id": "demo",
    "name": "california-weather",
    "type": "nws_weather",
    "area": "CA",
    "license": "U.S. government public data; attribution reviewed by operator"
  }
]
```

Set `SUBSTRATA_EVENT_FEEDS_FILE`, add `api.weather.gov` to
`SUBSTRATA_EVENT_ALLOWED_HOSTS`, and set `SUBSTRATA_NWS_USER_AGENT` to an
identifying application string with an operator contact. Each feed must include
its own reviewed license/attribution note. The adapter reads active alerts only,
does not poll every state automatically, and applies the normal tenant rules,
deduplication, event matching and analyst review pipeline. A `json_api` feed uses
`url`, `records_path`, `id_field`, `title_field` and `observed_at_field` to map a
provider's event JSON; `description_field`, `category_hint` and `api_key_file` are
optional. Credentials are read from a file and sent as a bearer token only to the
allowlisted HTTPS host. This generic interface does not establish provider
licensing or sanctions-screening suitability.

The `ofac_sdn` adapter reads OFAC's current SDN XML from the official
[Sanctions List Service](https://ofac.treasury.gov/sanctions-list-service); add
`sanctionslistservice.ofac.treas.gov` to the host allowlist and set
`SUBSTRATA_OFAC_USER_AGENT` to an identifying application/contact string as
described in [OFAC's technical notice](https://ofac.treasury.gov/sdn-list-data-formats-data-schemas/ofac-technical-actions-in-reverse-chronological-order/20240516_44).
The response is capped at 40 MB and 50,000 entries. Only supplier names and SDN
primary/alias names are compared. Exact matches and a bounded 0.90 name-similarity
heuristic create `needs_review` events; sanctions events are never auto-matched.
The displayed similarity is Substrata's string score, not OFAC's score. This
adapter does not cover OFAC's consolidated non-SDN list, export-control lists,
identifiers or jurisdiction/activity restrictions, and does not establish a true
match, false positive, clearance or instruction to block. Analysts must review the
complete source entry and apply their organisation's sanctions procedures; an
event-to-entity mapping is not a sanctions disposition. Historical candidates
remain event records, so operators must consider each event's source observation
time when reviewing it.

`/platform/jobs` stores idempotent work with leases, bounded retries and audit
records. Run `python scripts/platform_worker.py --tenant demo` as a separately
supervised process; each worker is bound to one tenant. The queue currently handles
event polls and deterministic assessments. The worker also scans tenant approval
deadlines on each poll, expires overdue pending decisions, closes the original
portal notice and creates an audited expiry notice. Approval endpoints enforce the
same deadline even when the worker is offline. Approval notices remain portal-only;
supplier confirmations and one reminder can be delivered through configured SMTP
over implicit TLS. The worker uses bounded attempts and delivery leases; SMTP's
external side effect is at-least-once if a process fails after sending but before
its database acknowledgement. Delivery stays disabled in development, even when
SMTP settings exist. SMS is not configured. There is no managed broker or automatic
worker orchestration yet.

For production supplier email, configure `SUBSTRATA_SMTP_HOST`,
`SUBSTRATA_SMTP_PORT` (implicit TLS, default 465), `SUBSTRATA_SMTP_FROM`, and,
when required by the mail server, `SUBSTRATA_SMTP_USERNAME` with a restricted
`SUBSTRATA_SMTP_PASSWORD_FILE`. Keep `SUBSTRATA_PII_KEY_FILE` separate from the
SMTP credentials. Delivery only processes tenant confirmation outbox records and
requires `SUBSTRATA_ENV` to be a non-development deployment mode.

The stateless authenticated `/platform/mcp` endpoint exposes typed tenant tools for
`graph.snapshot`, `evidence.discover`, `event.submit`, `cascade.assess`,
`mitigation.propose`, `approval.decide` and `audit.verify`. The A2A agent card
advertises the same task skills at `/platform/a2a`; each call applies the same
tenant and role checks as the REST service. The cascade remains plain Python and
no model computes exposure numbers. Tests cover discovery, representative tool
calls, authentication, tenant isolation and results, but do not claim broad client
interoperability or streaming support.

Authenticated `/platform` endpoints derive tenant and actor from verified access
tokens. Roles are `viewer`, `analyst`, `approver`, `admin`; body/header tenant
overrides are never trusted. Tokens require issuer, audience, expiry, issued/not
before timestamps and tenant/role claims. Production accepts configured asymmetric
OIDC verification; SAML organisations use an identity provider that brokers SAML
to OIDC with the same verified claims. Configure tenant/role mappings at the IdP.
HMAC development credentials are refused outside explicit development mode.
Platform mode disables unauthenticated replay/reset routes by default.
CI also runs PostgreSQL-backed tests with a non-superuser `NOBYPASSRLS` role,
checks tenant-scoped row visibility and rejects a cross-tenant insert. Local runs
skip this integration test unless `SUBSTRATA_TEST_POSTGRES_ADMIN_URL` is set.

Install `python -m pip install -e ".[dev,platform]"`. Run migrations explicitly:
`python -m substrata.platform.cli migrate` with `SUBSTRATA_PLATFORM_DATABASE_URL`.
For local development, set `SUBSTRATA_ENV=development`,
`SUBSTRATA_AUTH_ALGORITHM=HS256`, an issuer and `SUBSTRATA_AUTH_KEY_FILE` ending in
`.secret`. `dev-key` creates a new random secret without overwriting an existing
one; `dev-token --tenant demo --role admin` emits a one-hour access token.
These commands are development-only. Never put verification secrets in browser
environment variables. CORS origins use `SUBSTRATA_CORS_ORIGINS`.

Audit JSON exports can be checked without a database using
`python -m substrata.platform.cli verify-audit --file export.json`. Store chain
heads separately to detect privileged tail truncation.

1. Tenant context, portable migrations, immutable graph/provenance and atomic audit.
2. Authenticated API, OIDC/RBAC, tenant policy and feature-flagged product access.
3. Imports/connectors, entity resolution and data-quality/onboarding workflows.
4. Multi-industry scenarios, deterministic cascade, uncertainty and graph exploration.
5. Retrieval/extraction, signed confirmations, scoring training and evaluation.
6. Feeds, durable jobs, MCP/A2A facades and exports are implemented in the offline
   slice; broader international weather and port feeds, additional sanctions and
   export-control lists, agent specialisations, approval notifications, managed
   queue orchestration and production operations remain.

The final review must map every requirement to executable tests, runtime behavior
or a documented external configuration gate. Real supplier contact is disabled in
development, execution defaults to dry-run, and no SAP affiliation is claimed.
No claims of production readiness follow merely from passing offline tests.
The local PostgreSQL/API/worker Compose scaffold and CI checks are in place;
request correlation, readiness and process counters are implemented. Production
secret management, TLS deployment, scheduled encrypted backups/restore drills,
distributed tracing, managed metrics, and a managed job broker remain explicit
pilot gates. See [Operations](OPERATIONS.md).
