# Prototype decisions

This register distinguishes implemented work from planned implementation choices.
All business data and actions in the prototype are synthetic or simulated.
**[Design]**

## D001: stop at small checkpoints

The user's explicit instruction on 8 October 2026 overrides the pasted brief's
continuous milestone execution and blanket no-push rule. M0 is split into four
checkpoints. Commit locally, explain the result and stop after each checkpoint;
push after user review, then start the next checkpoint only when directed.
The requested working branch is `feat/prototype-vertical-slice`.

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

## Open implementation decisions

- **M2 formulas:** the README defines the 18-day cover and 72-day exposure worked
  example, but does not provide the claimed depth spec, a priority equation or
  full shared-dependency/path-confidence rules. Record precise deterministic
  rules and any assumptions before implementing them. The supplied brief's
  product-along-path and noisy-OR-across-paths requirements remain inputs to that
  decision. **[TBD]**
- **M1 scenario size:** EVALUATION.md describes a minimum fixture and explicitly
  leaves final generator size open. Freeze and record generator parameters
  before producing data. **[TBD]**
- **M3 thresholds and M4 spend limit:** choose explicit configurable assumptions;
  do not present them as calibrated or real procurement policy. **[TBD]**

## Deferred scope

SAP HANA/BTP/Joule adapters, live public-signal and ownership calls, model
training, MCP transport, authentication and production deployment remain TODOs
outside this prototype pass. **[Design]** No SAP integration or evaluation result
is claimed.
