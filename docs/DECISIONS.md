# Prototype decisions

This register distinguishes implemented work from planned implementation choices.
All business data and actions in the prototype are synthetic or simulated.
**[Design]**

## D001: stop at small checkpoints

The user's explicit instruction on 8 October 2026 overrides the pasted brief's
continuous milestone execution and blanket no-push rule. M0 is split into four
checkpoints. Commit locally, explain the result and stop after each checkpoint;
start the next checkpoint only when directed. The requested working branch is
`feat/prototype-vertical-slice`.

The user subsequently requested pushes after every five new commits. The batch
count begins after `5a330b8`, the existing M0.3 commit; that unpushed commit goes
with the first batch. This changes push cadence, not checkpoint review stops.
Do not pad the history with commits solely to trigger a push.

The user's latest instruction supersedes the review stops: continue to the
complete working vertical slice, provide progress updates, then report completion.
Retain meaningful checkpoint commits and the five-commit push cadence.

## D002: Python version follows the specification

TECH_STACK.md specifies Python 3.12+; the pasted brief says 3.11+. Follow the docs:
`pyproject.toml` now requires Python 3.12+.
The inspected workstation provides Python 3.13.5, Node.js 24.14.0 and npm 11.9.0.
The M0.2 backend installation and checks passed on Python 3.13.5. Other Python
versions have not yet been verified. M0.3 also verifies the frontend on Node.js
24.14.0 / npm 11.9.0.

## D003: orchestration stays in process

Use the documented plain typed async state-machine fallback for the first
prototype. Keep agent/tool interfaces separate from orchestration so a later
LangGraph runner can reuse them. MCP servers and A2A wrappers are outside this
pass. This is a planned choice; no orchestration code exists yet. **[Design]**

## D004: commands must match the current checkpoint

Do not publish Getting started commands before they have been run successfully.
GNU Make is absent from the inspected Windows shell, so the command checkpoint
must include a verified Windows entry point alongside the requested Makefile.
**[Design]**

## D005: minimal backend package and pinned dependencies

M0.2 adds the installable `backend/substrata` package, an app factory, a typed
`/health` process-liveness response and generated OpenAPI documentation. Health
does not check a database, invoke an LLM or claim scenario readiness.

`pyproject.toml` pins direct runtime, development and build dependencies;
`requirements-dev.lock` records the resolved runtime/development versions. The
verified install command uses the lock as pip constraints. Add SQLAlchemy,
NetworkX and other dependencies when their implementation starts, rather than
installing unused libraries at this checkpoint. **[Design]**

The resolved Starlette 1.7.0 test client recommends HTTPX2 and warns on the older
HTTPX fallback. Use pinned HTTPX2 for tests; the final test run has no warnings.
Default Swagger UI assets still use a CDN. The API and OpenAPI JSON operate
offline after installation; self-hosted documentation assets are deferred.
**[Design]**

## D006: static frontend scaffold

This section records the historical M0.3 checkpoint. D015 describes the completed
interactive API/SSE dashboard; the dependency caveats below still apply.

M0.3 adds a Next.js App Router / TypeScript / Tailwind workspace, with an explicit
synthetic-data label, a network empty state and a description of the planned
workflow. No supplier records, API status, graph interactions, replay controls
or approvals are fabricated. The workflow link is an in-page anchor.

Use `output: "export"` for standalone static output. The current page has no API
calls, Server Actions or route handlers. System fonts and inline SVG artwork
keep the exported page independent of external font/image services. Graph and
SSE integrations remain deferred to their domain milestones. **[Design]**

`package.json` pins direct dependencies; `package-lock.json` pins transitive
resolutions. Node.js 24.x is the chosen frontend runtime. `typecheck` generates
Next.js route types before running TypeScript so a clean checkout does not
depend on a previous development or production build. **[Design]**

### Development-tool limitations observed on 8 October 2026

- ESLint 10 triggers peer-range conflicts in the current lint plugins. Use
  ESLint 9.39.5 for compatibility; npm marks that release unsupported. Update the
  lint stack when the plugins support the current ESLint release. **[TBD]**
- Full npm audit reports five high-severity entries from one development-only
  dependency chain: `eslint-config-next` → `@next/eslint-plugin-next` →
  `fast-glob` → `micromatch` → `braces`. The
  [braces advisory](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm)
  concerns deeply nested glob patterns. The registry's latest `braces` release,
  3.0.3, is still in the affected range. No patched upgrade is available at this
  checkpoint; do not apply the audit suggestion to downgrade the Next.js lint
  configuration across major versions. Recheck for an upstream patch before
  accepting external glob configuration or preparing production tooling.
  **[TBD]**
- `npm audit --omit=dev` reports zero vulnerabilities for runtime dependencies
  at this checkpoint. This is a point-in-time check, not a security guarantee.

## D007: one local command runner

`scripts/dev.py` provides setup, seed, test, lint, api, ui, demo and build tasks.
The Makefile forwards each target to that runner so platform-specific lifecycle
logic has one implementation. GNU Make is absent on this workstation; Python
commands are the verified Windows path. Makefile targets are supplied but not
locally executed with GNU Make.

Setup installs locked Python/frontend dependencies and copies `.env.example`
only when `.env` does not exist. The root `.env` configures the launcher ports;
shell values override it. Both servers bind to loopback. The runner rejects
invalid/conflicting ports and detects occupied ports before launching servers.
Pinned `python-dotenv` is a development dependency used to read this file.

API and UI run as child processes owned by the runner. Windows children inherit
the console so Ctrl+C reaches them; cleanup can terminate only an owned child
tree with the native process tool. POSIX children use separate process groups.
A supervisor stops the other server if one exits and cleans up through the
local virtual-environment runner on interruption. This is local development
tooling, not a production process manager. **[Design]**

Next.js regenerates `next-env.d.ts` with different paths in development and
production. Follow the installed framework guide: keep this generated file
ignored and untracked. The typecheck command regenerates it on a clean checkout.

At this checkpoint, `seed` creates nothing and says M1 is pending; `demo` starts
the API health scaffold and frontend shell. It does not claim the six-step
supply-chain scenario works. `test` runs pytest plus frontend type checking;
`lint` checks Python lint/formatting and frontend ESLint. Browser automation
tests remain deferred to interactive UI features. **[Design]**

## D008: explicit database foundation before domain schema

M1.1 uses SQLAlchemy 2.0.54 (the maintained 2.0 series) and Alembic 1.20.0,
with resolved dependencies pinned in the Python lock. SQLite uses WAL,
foreign-key enforcement and a five-second busy timeout on every connection.
Python's non-legacy transaction mode (`autocommit=False`) gives explicit
commit/rollback behavior, including transactional DDL. The configuration follows
[SQLAlchemy's SQLite guidance](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html)
and [Alembic connection sharing](https://alembic.sqlalchemy.org/en/latest/cookbook.html#sharing-a-connection-across-one-or-more-programmatic-migration-commands).

The explicit `migrate` task upgrades `data/substrata.sqlite3`, independent of
the launcher's working directory. It never resets or seeds data. Importing or
starting the API performs no database work; health remains process liveness.
The initial revision establishes only Alembic history. Graph/evidence and ERP
tables follow in M1.2/M1.3; run, approval, audit and evaluation tables follow with
their features in M3/M4. Existing migration revisions stay immutable.
PostgreSQL configuration and migrations are not verified at this checkpoint.

## D009: versioned graph schema and primary evidence

M1.2 stores graph identity as `(id, graph_version)`. Endpoint IDs, types and
versions use composite foreign keys, so an edge cannot silently cross versions
or claim a component is a supplier site. Node-specific attributes use validated
Pydantic JSON payloads; display and normalized names stay indexed relational
columns. This avoids a separate sparse table for each entity in the prototype.
Application validation checks the full payload; SQL checks its discriminator.
Future services must replace attribute payloads rather than mutate nested JSON.

Every inferred edge has a primary supporting citation. A foreign key ensures
the evidence exists; SQLite triggers create its association and prevent its
removal or alteration while primary. Other evidence can support or contradict.
Changing the primary citation retains the prior link and cannot promote a
contradictory citation. `source_ids` will be projected from `edge_evidence`
rather than separately stored. This follows SQLite's
[trigger and constraint mechanism](https://www.sqlite.org/lang_createtrigger.html).

The M3 human confirmation workflow does not exist yet. A temporary trigger
blocks updates from any other status into `confirmed`. Initial pre-confirmed
fixtures may be inserted with a verification timestamp; no API exposes this.
The later workflow will replace this gate with confirmation-record checks in
a new migration. This checkpoint makes no authorization or immutable-history
claim. Rejection and expiry keep rows and evidence.

Ownership uses the documented site-to-site option; a separate legal-entity
model is deferred. Location supports sites/plants and region nesting.
Alternative-supplier references and event source IDs in payloads will be
cross-checked by the seed/workflow service, and authoritative external-ID
uniqueness is deferred until identifier authority is modelled. All graph nodes
are synthetic; source kind separately distinguishes synthetic evidence from
public event context. No data has been seeded or ingested.

JSON discriminator checks, hash-format checks and evidence/confirmation
triggers currently target SQLite. PostgreSQL portability remains unverified.
Use the migration command for initialization; ORM `create_all()` alone does
not install these triggers. Migration files contain their own frozen schema
definitions and do not import current models.

## D010: frozen synthetic scenario and ownership scope

Generator v1 uses seed 42 and the evaluation document's minimum: one OEM/product,
eight components, twelve sites, four regions, two plants, five alternative
candidates, six events and three low-confidence confirmation candidates.
`scenario.json` contains declared edges only; `true_graph.json` separately keeps
hidden truth. Only evaluation and simulated replies may consult hidden truth.
The mapper receives the observable graph and invented corpus, never hidden IDs
or labels. Fixture hashes and generator parameters are recorded.

The documented graph schema has no site-to-site supply edge. This demo therefore
models a shared **ownership/control** dependency using the documented OWNED_BY
edge: three apparently independent groups share one semiconductor parent.
Cascade propagation from a disrupted parent to controlled sites is an explicit
scenario assumption, not proof that ownership always implies supply disruption.
This preserves documented edge directions rather than inventing real procurement
relationships. All names, quantities, claims and events are invented. Public
Nexperia context motivates the story only; there is no assertion about its
private suppliers or inventory. A full component-to-producing-site procurement
model remains a future extension.

Reset downgrades/re-upgrades and reloads the synthetic database in one SQLite
transaction. A failed reset rolls back schema and data. It never deletes paths
or contacts an external system. Seeding requires an initialized database and
clears prior demo runs/approvals when those tables exist.

## D011: deterministic formulas and bounded graph projection

The README supplies the cover/exposure example but no depth/API formula sketch.
Formula version `runway-v1` defines cover = (on_hand + eligible_in_transit) /
daily_consumption; exposure = max(0, requalification_days - cover). Zero demand
returns `no_demand`, null cover and zero exposure; missing inputs or unit/snapshot
mismatch return `incomplete` with no invented numerical answer. Shipments count
only if they arrive before available stock is exhausted. Priority is an
uncalibrated 0–100 ordering score: 100 × severity × path_confidence ×
exposure / max(requalification_days, 1). **[Assumption]**

Paths multiply edge confidence; alternative simple paths combine with noisy-OR
(1 - product(1 - path_score)). This is an explanatory score, not a calibrated
probability: paths may share evidence. Ownership/location reverse for event
propagation; supply/where-used edges follow their stored direction. Rejected,
expired and out-of-validity edges are excluded. Traversal bounds depth at 8,
paths at 128 and work at 10,000, returning explicit truncation instead of looping
on cycles. Approval policy must block incomplete/truncated impact results.

## D012: mock extraction and measured fixture evaluation

Historical initial provider decision; D016 supersedes the default mock and generic HTTP adapter.

The first Mapper is a narrow exact-name/ownership-sentence baseline. Co-location
and similar names can retrieve distractors but cannot establish a relationship.
Embeddings/fuzzy/category heuristics are deferred; the client interface includes
embedding methods for a later comparison. No trained or pretrained semantic
model is claimed by the default mock. A configurable HTTP JSON adapter exists;
live provider access is optional and not verified. SAP Generative AI Hub remains
a documented adapter TODO rather than an unused implementation stub.

All extraction JSON is Pydantic-validated; exact quotes must occur in the cited
source and name both exact endpoints in the supported ownership sentence form.
The whole batch validates before writes; invalid output fails closed and records
a failed agent run. Provider/model, prompt, measured latency, schema outcome,
validated extraction and tool summary are retained. Confidence is the explicit
uncalibrated rule `0.8 * source_reliability + 0.2 * exact_endpoint_match`.
Default inference threshold is 0.75. Lower scores queue confirmation without
silently adding a graph edge. **[Assumption]**

Simulated replies alone may consult the truth fixture, with configurable seeded
noise. A matching persisted response is required before confirmation status can
change. This models a supplier reply, not a real supplier communication or
human procurement approval. Three low-confidence fixture candidates yield two
confirmations and one rejection at zero noise.

Evaluation runs on a fresh temporary database with configurable masking of
the four hidden ownership relationships. It persists raw predictions/errors,
counts and metrics and generates the results section only after execution.
This frozen template fixture is not a held-out generalisation benchmark; no
weights were tuned and no model was trained. Warning gain assumes Tier-1-only
alerting at stock exhaustion and deep alerting at the event; it is calculated
stock headroom under that assumption, not measured enterprise warning time.

## D013: simulated options, snapshot approval and audit

Five mitigation templates use invented USD cost, duration and risk assumptions,
ranked by 0.4 × cost/25000 + 0.35 × duration/90 + 0.25 × risk (lower is first).
These estimates do not claim supplier availability, plant capacity or commercial
feasibility. Default spend limit is USD 10,000; alternate-source qualification
and reallocation always require review. Low-spend allowed actions record a
preview only. Unknown actions, incomplete/truncated impacts or zero exposure
are blocked. **[Assumption]**

Approval requires a name, demo planning/procurement role and reason. Roles are
self-declared in this local prototype; identity/authentication remain out of
scope. Approval pins graph/evidence, ERP input hashes, dataset, formula and
policy configuration. Changed inputs, policy or expiry invalidate the request;
duplicates are rejected. Approving one option supersedes other pending options
for the same scenario. No approval sends an external transaction.

Audit records hash canonical payload plus sequence, previous hash, actor, type
and UTC timestamp. SQLite triggers reject ordinary updates/deletes, and every
append verifies the existing chain. A corrupt chain blocks further decisions.
Copied record mutation and gaps are detected; tail truncation requires a
previously trusted head hash. There is no external anchor, signature or claim
that hashing proves source truth. Reset intentionally discards demo history.
The local single-process runtime serializes mutations; distributed workers and
production concurrency are outside scope.

## D014: local API, replay recovery and SSE

The README contains no API sketch; the implemented contract uses `/state`,
`/graph`, `/mapper/run`, `/confirmations/simulate`, `/replay/start|pause|reset`,
`/events/{id}/resolve`, `/scenarios/{id}/refresh`, `/approvals/{id}/decision`,
`/audit/verify` and `/stream`. OpenAPI publishes request bodies and the workspace
schema. CORS permits the configured loopback UI port. SSE reads persisted events
directly from FastAPI, with generation/cursor IDs, heartbeat and reset handling;
`once=true` provides a bounded diagnostic response.

Exact event names match deterministically. Non-exact candidates enter analyst
review; no uncertain match triggers a cascade automatically. Severity comes
from the validated synthetic event fixture. Replay handles the next unseen
event, can pause between events and resets only synthetic data. Refresh creates
a new frozen scenario instead of editing previous calculations. An input-file
hash also pins the replay source for approval validity.

The app factory/health endpoint still perform no database or network work.
First workflow access checks readiness and gives setup/seed guidance if missing.
Environment settings are loaded by the launcher; D016 later changes the application default to Gemini.
One local process serializes mutations and replay. All raw audit timestamps,
agent run IDs and SSE generations are intentionally variable; repeatability
tests compare canonical graph, calculated reports and action/decision outputs.
Ten complete seeded mock replays produce identical semantic hashes, with a
valid audit chain on every run. This does not assert identical wall-clock logs.

## D015: browser dashboard and portable build

The client-only Cytoscape graph uses an explicit dynamic import with SSR disabled;
its presentation layout does not calculate dependency risk. Node shapes distinguish
types; status styles and evidence quotes expose uncertainty. Keyboard users can
inspect the same relationships through a native select. API/SSE state drives replay,
runway, simulated action payloads, named approval and audit panels. UI formatting
never computes business metrics. Error banners, empty panels, disabled controls,
inline reset confirmation and graph fallback handle unavailable/incomplete state.

Static output needs a running FastAPI service; it contains no Next.js API routes or
Server Actions. The runner shares root .env/shell configuration between dev and build,
embedding the selected API URL at build time. Fonts are local/system resources.
The HTTP LLM adapter was contract-tested with mocked transport, not a real provider.
Full npm audit retains the development lint-chain advisory in D006; runtime audit
must be reported separately. The dashboard is a local single-worker prototype.

## D016: Gemini primary and Grok backup — 8 October 2026

At the user's request, Gemini is the application's primary LLM and xAI Grok is
its backup. Fixed official HTTPS endpoints replace the generic compatible HTTP
adapter; no OpenAI service or SDK is used. Models, keys and a bounded timeout
are configured through backend environment variables. See [LLM setup](LLM_SETUP.md)
for current defaults, source API contracts and activation instructions.

Every extraction tries Gemini first, then Grok once on transport/provider or
JSON-schema failure. It never silently substitutes mock output. Missing keys
leave the dashboard available and produce a guided 503 on extraction. The UI
shows credential presence, not a claimed successful connection. Attempt metadata
and the actual answering model are persisted; secret values/upstream error bodies
are excluded. Exact-quote/endpoints validation and all business math remain
outside the models. Semantic embedding retrieval remains deferred.

Explicit mock mode and isolated mock-only evaluation retain the repeatable demo.
The user will provide keys later, so live model quality, billing and account access
are not verified. Historical mock graph/scenario records are preserved.

## Resolved initial implementation questions

- Formula/priority and bounded path traversal: D011 records the exact assumptions.
- Scenario size and hidden relationships: D010 fixes generator 1.0 and seed 42.
- Inference threshold and spend policy: D012/D013 record configurable, uncalibrated
  demo assumptions. They are not enterprise procurement policy.

## Deferred scope

SAP HANA/BTP/Joule adapters, live public-signal retrieval, live provider verification, model
training, MCP transport, authentication and production deployment remain TODOs
outside this prototype pass. **[Design]** No SAP integration is claimed. Measured
frozen synthetic-fixture results are generated in EVALUATION.md.
