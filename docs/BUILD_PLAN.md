# Prototype build checkpoints

The implementation follows README.md, ARCHITECTURE.md, DATA_MODEL.md,
TECH_STACK.md, EVALUATION.md and RESEARCH.md. The demo uses synthetic data and
simulated actions only. **[Design]**

## Working agreement

The user originally requested review stops after each checkpoint. Their latest
instruction asks to continue until everything is done and then report completion.
Continue through the remaining vertical slice, verify and commit each meaningful
checkpoint, and provide progress updates without requiring intermediate review.

The user updated the push policy on 8 October 2026: push after every five new
commits, starting after `5a330b8` (the existing M0.3 commit). Include that existing
unpushed commit in the first batch. Count actual commits with
`git rev-list --count 5a330b8..HEAD`; push at each multiple of five. Do not create
extra commits just to reach the batch size. The latest instruction removes the
intermediate review stops; it preserves the five-commit push cadence.

Working branch: `feat/prototype-vertical-slice`.

## M0: scaffold, split into small steps

| Checkpoint | Deliverable | Status |
|---|---|---|
| M0.1 | Specification review, project folders, Git ignore rules and this checklist | Complete and pushed |
| M0.2 | Minimal FastAPI app, health endpoint, pinned Python dependencies, pytest and Ruff configuration | Complete and pushed; API scaffold only |
| M0.3 | Minimal Next.js / TypeScript / Tailwind app, synthetic-data label and verified static build | Complete; workspace scaffold only |
| M0.4 | Verified setup, seed, test, lint, api, ui and demo entry points; `.env.example`; README commands | Complete; scaffold commands only |

`seed` reports that scenario seeding is pending until M1. `demo` launches the
scaffold only. GNU Make is not available in the current shell: use the verified
Python runner on Windows. Makefile forwarding targets are supplied but have not
been executed with GNU Make here.

## M1: persistence and synthetic data, split into small steps

| Checkpoint | Deliverable | Status |
|---|---|---|
| M1.1 | SQLite WAL engine, transaction helper, Alembic baseline and explicit migration command | Complete; infrastructure only |
| M1.2 | Graph entities, edges, evidence and source snapshot schema with constraints | Complete; empty schema only |
| M1.3 | Synthetic ERP schema with units, inventory timestamps and dataset versions | Complete; empty schema |
| M1.4 | Deterministic seed and separate true/declared graphs | Complete |
| M1.5 | Synthetic evidence corpus, seed integrity checks and reset/reseed verification | Complete; combined with the fixture checkpoint |

Run-state, approval, audit and evaluation tables will be introduced with their
own feature checkpoints in M3/M4, rather than creating unused tables now.

## Later milestones

These remain planned. Before starting each milestone, split it into small,
reviewable checkpoints and update this checklist. **[Design]**

| Milestone | Scope | Status |
|---|---|---|
| M1 | Database schema, deterministic seed, separate true/declared graphs and synthetic evidence | In progress; M1.1–M1.2 complete |
| M2 | GraphStore, deterministic cascade formulas and edge-case tests | Complete; formula assumptions recorded in D011 |
| M3 | Mock-first LLM interface, evidence-backed Mapper, supplier confirmations and measured evaluation | Complete; narrow fixture baseline, limitations in D012 |
| M4 | Event replay, ranked simulated actions, approval gate, hash-chained audit, API and SSE | Planned |
| M5 | Graph, replay feed, cascade card, approval queue, audit view and demo script | Planned |

## Current verification

M0.1 verified repository structure, ignored local artifacts and whitespace.

M0.2 verification on Windows / Python 3.13.5:

- Installed the editable project and development tools with the dependency lock.
- Two pytest API contract tests passed with no warnings.
- Ruff lint and formatting checks passed; `pip check` found no broken requirements.
- A real Uvicorn server returned the expected JSON from `/health` on port 8000;
  `/openapi.json` and `/docs` returned HTTP 200. Stopped the verification server.

M0.3 verification on Windows / Node.js 24.14.0 / npm 11.9.0:

- Lockfile installation, frontend lint, TypeScript checking and static build passed.
- Served `frontend/out/` independently of Next.js and the API; checked the page in
  the browser, including its synthetic-data label and working workflow link.
- Inspected desktop and 390-pixel phone layouts; the phone layout stacks panels
  without horizontal overflow. Browser console showed no warnings or errors.
- Existing backend tests and Ruff checks still passed.
- Runtime npm audit reported zero vulnerabilities. The development lint tool
  limitations are recorded in D006; full dependency audit is not clean.

M0.4 adds the common Python command runner, Makefile targets and `.env.example`.
Port defaults, shell-over-file precedence, invalid values and conflicting API/UI
ports are covered by tests. Setup preserves existing local configuration. The
`seed` command remains an explicit placeholder.

- Setup, test, lint, seed and static build tasks passed through the runner;
  pytest reports nine passing tests.
- Standalone API/UI and the combined demo served the expected health response
  and synthetic workspace.
- Ctrl+C stopped both demo servers and released both ports. Stopping a
  standalone API left the separately started UI running.
- An occupied port was rejected before starting another server.
- Root `.env` is ignored; `.env.example` remains trackable. Python dependency
  checks passed. The existing frontend development-tool advisory remains.
- GNU Make forwarding and non-Windows process behavior remain unverified locally.

M1.1 adds pinned SQLAlchemy/Alembic dependencies, explicit schema upgrades and
transaction boundaries. Real temporary SQLite files verify per-connection WAL,
foreign-key enforcement, busy timeout, commit/rollback, concurrent reads during
a pending write and repeated migrations preserving existing test records.
The baseline creates only `alembic_version`; no business tables or data yet.

- All 15 pytest tests and frontend type checking passed through the runner.
- Python lint/format checks and frontend ESLint passed through the runner.
- The migration command succeeded twice against the ignored local database.
- Locked Python installation and `pip check` passed. No frontend source changed,
  so the previously verified static build was not repeated.

M1.2 adds the five graph/provenance tables, seven validated node attribute
shapes, typed versioned endpoints and source/evidence integrity constraints.
Migration-owned SQLite triggers ensure inferred edges have supporting evidence
and block updates into confirmed until the M3 human workflow is implemented.
Schema tests cover persistence, invalid records, provenance retention, UTC
handling, migration/ORM agreement and empty-database downgrade/re-upgrade.

- All 78 pytest tests and frontend type checking passed through the runner.
- Python lint/format checks, frontend ESLint and `pip check` passed.
- The existing local baseline upgraded to `0002_graph_provenance`; a second
  migration run succeeded. All five domain tables have zero rows and all five
  migration-owned triggers are installed.
- No frontend source changed; the static build was not repeated. No graph API,
  scenario data or confirmation workflow is claimed at this checkpoint.

These checks verify the foundations, not the full supply-chain workflow.
M1.3 verified 86 passing tests and Ruff checks, then upgraded the local database.
The next checkpoint is the deterministic scenario and synthetic evidence corpus.
